from nltk.tokenize import word_tokenize
import nltk

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

from pathlib import Path
import librosa
import scipy
import torch
import torchaudio
from cached_path import cached_path
torch.manual_seed(0)
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True

import random
random.seed(0)

import numpy as np
np.random.seed(0)

from langchain.text_splitter import RecursiveCharacterTextSplitter
import yaml

from . import models
from . import utils
from .phoneme import PhonemeConverterFactory
from .text_utils import TextCleaner
from .Utils.PLBERT.util import load_plbert
from .Modules.diffusion.sampler import DiffusionSampler, ADPM2Sampler, KarrasSchedule

import logging
# Configure logging
logging.basicConfig(
    level=logging.INFO, # (works for all levels above debug: info, warning, error,critical)
    format='%(asctime)s - %(levelname)s - %(message)s', # time stamp, level name, message to be displayed
    filename='/home/hamna/Desktop/Internship-2024/tts.log', # file where log is saved
    filemode='w' # file created in write mode (overwrites existing file if present)
)



LIBRI_TTS_CHECKPOINT_URL = "/home/hamna/Desktop/Internship-2024/style2_tts/Models/LibriTTS/epochs_2nd_00020.pth"
LIBRI_TTS_CONFIG_URL = "/home/hamna/Desktop/Internship-2024/style2_tts/Models/LibriTTS/config.yml"
DEFAULT_TARGET_VOICE_URL = "/home/hamna/Desktop/Internship-2024/style2_tts/StyleTTS2/Demo/reference_audio/amused.wav"
SINGLE_INFERENCE_MAX_LEN = 420

to_mel = torchaudio.transforms.MelSpectrogram(
    n_mels=80, n_fft=2048, win_length=1200, hop_length=300)
mean, std = -4, 4


def length_to_mask(lengths):
    mask = torch.arange(lengths.max()).unsqueeze(0).expand(lengths.shape[0], -1).type_as(lengths)
    mask = torch.gt(mask+1, lengths.unsqueeze(1))
    return mask


def preprocess(wave):
    wave_tensor = torch.from_numpy(wave).float()
    mel_tensor = to_mel(wave_tensor)
    mel_tensor = (torch.log(1e-5 + mel_tensor.unsqueeze(0)) - mean) / std
    return mel_tensor


def segment_text(text):
    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", " ", ""],
        chunk_size=SINGLE_INFERENCE_MAX_LEN,
        chunk_overlap=0,
        length_function=len,
    )
    segments = splitter.split_text(text)
    return segments


class StyleTTS2:
    def __init__(self, model_checkpoint_path=None, config_path=None, phoneme_converter='gruut'):
        self.model = None
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.phoneme_converter = PhonemeConverterFactory.load_phoneme_converter(phoneme_converter)
        self.config = None
        self.model_params = None
        self.model = self.load_model(model_path=model_checkpoint_path, config_path=config_path)

        self.sampler = DiffusionSampler(
            self.model.diffusion.diffusion,
            sampler=ADPM2Sampler(),
            sigma_schedule=KarrasSchedule(sigma_min=0.0001, sigma_max=3.0, rho=9.0), # empirical parameters
            clamp=False
        )


    def load_model(self, model_path=None, config_path=None):

        if not model_path or not Path(model_path).exists():
            print("Invalid or missing model checkpoint path. Loading default model...")
            model_path = cached_path(LIBRI_TTS_CHECKPOINT_URL)

        if not config_path or not Path(config_path).exists():
            print("Invalid or missing config path. Loading default config...")
            config_path = cached_path(LIBRI_TTS_CONFIG_URL)

        self.config = yaml.safe_load(open(config_path))

        # load pretrained ASR model
        ASR_config = Path("/home/hamna/Desktop/Internship-2024/style2_tts/StyleTTS2/Utils/ASR/config.yml").resolve()
        ASR_path = Path("/home/hamna/Desktop/Internship-2024/style2_tts/StyleTTS2/Utils/ASR/epoch_00080.pth").resolve()
        text_aligner = models.load_ASR_models(ASR_path, ASR_config)

        # load pretrained F0 model
        F0_path = Path("/home/hamna/Desktop/Internship-2024/style2_tts/StyleTTS2/Utils/JDC/bst.t7").resolve()   
        pitch_extractor = models.load_F0_models(F0_path)
       
        # load BERT model
        BERT_dir_path = Path('PLBERT_dir', "/home/hamna/Desktop/Internship-2024/style2_tts/StyleTTS2/Utils/PLBERT").resolve()  # Directory at BERT_dir_path should contain PLBERT config.yml AND checkpoint
        plbert = load_plbert(str(BERT_dir_path))

        self.model_params = utils.recursive_munch(self.config['model_params'])
        model = models.build_model(self.model_params, text_aligner, pitch_extractor, plbert)
        _ = [model[key].eval() for key in model]
        _ = [model[key].to(self.device) for key in model]

        params_whole = torch.load(model_path, map_location='cpu')
        params = params_whole['net']

        for key in model:
            if key in params:
                print('%s loaded' % key)
                try:
                    model[key].load_state_dict(params[key])
                except:
                    from collections import OrderedDict
                    state_dict = params[key]
                    new_state_dict = OrderedDict()
                    for k, v in state_dict.items():
                        name = k[7:] # remove `module.`
                        new_state_dict[name] = v
                    # load params
                    model[key].load_state_dict(new_state_dict, strict=False)
        _ = [model[key].eval() for key in model]

        return model


    def compute_style(self, path):
        wave, sr = librosa.load(path, sr=24000)
        audio, index = librosa.effects.trim(wave, top_db=30)
        if sr != 24000:
            audio = librosa.resample(audio, sr, 24000)

        mel_tensor = preprocess(audio).to(self.device)

        with torch.no_grad():
            ref_s = self.model.style_encoder(mel_tensor.unsqueeze(1))
            ref_p = self.model.predictor_encoder(mel_tensor.unsqueeze(1))
        return torch.cat([ref_s, ref_p], dim=1)
    

    def inference(self,
                  text: str,
                  target_voice_path=None,
                  output_wav_file=None,
                  output_sample_rate=24000,
                  alpha=0.3,
                  beta=0.7,
                  diffusion_steps=5,
                  embedding_scale=1,
                  ref_s=None):

        logging.info("Inside the inference function")
        # BERT model is limited by a tensor size [1, 512] during its inference, which roughly corresponds to ~450 characters
        if len(text) > SINGLE_INFERENCE_MAX_LEN:
            logging.info("Long inference called")
            return self.long_inference(text,
                                       target_voice_path=target_voice_path,
                                       output_wav_file=output_wav_file,
                                       output_sample_rate=output_sample_rate,
                                       alpha=alpha,
                                       beta=beta,
                                       diffusion_steps=diffusion_steps,
                                       embedding_scale=embedding_scale,
                                       ref_s=ref_s)

        if ref_s is None:
            logging.info("entering computing style")
            ref_s = self.compute_style(target_voice_path)  # target style vector
            logging.info("returning from computing style")

        text = text.strip()
        text = text.replace('"', '')
        phonemized_text = self.phoneme_converter.phonemize(text)
        ps = word_tokenize(phonemized_text)
        phoneme_string = ' '.join(ps)

        textcleaner = TextCleaner()
        tokens = textcleaner(phoneme_string)
        tokens.insert(0, 0)
        tokens = torch.LongTensor(tokens).to(self.device).unsqueeze(0)

        with torch.no_grad():
            logging.info("inside with part")
            input_lengths = torch.LongTensor([tokens.shape[-1]]).to(self.device)
            text_mask = length_to_mask(input_lengths).to(self.device)
            t_en = self.model.text_encoder(tokens, input_lengths, text_mask)
            bert_dur = self.model.bert(tokens, attention_mask=(~text_mask).int())
            d_en = self.model.bert_encoder(bert_dur).transpose(-1, -2)

            s_pred = self.sampler(noise = torch.randn((1, 256)).unsqueeze(1).to(self.device),
                                  embedding=bert_dur,
                                  embedding_scale=embedding_scale,
                                  features=ref_s, # reference from the same speaker as the embedding
                                  num_steps=diffusion_steps).squeeze(1)

            s = s_pred[:, 128:]
            ref = s_pred[:, :128]

            ref = alpha * ref + (1 - alpha)  * ref_s[:, :128]
            s = beta * s + (1 - beta)  * ref_s[:, 128:]

            # duration prediction
            d = self.model.predictor.text_encoder(d_en,
                                                  s, input_lengths, text_mask)

            x, _ = self.model.predictor.lstm(d)
            duration = self.model.predictor.duration_proj(x)

            duration = torch.sigmoid(duration).sum(axis=-1)
            pred_dur = torch.round(duration.squeeze()).clamp(min=1)

            pred_aln_trg = torch.zeros(input_lengths, int(pred_dur.sum().data))
            c_frame = 0
            for i in range(pred_aln_trg.size(0)):
                pred_aln_trg[i, c_frame:c_frame + int(pred_dur[i].data)] = 1
                c_frame += int(pred_dur[i].data)

            # encode prosody
            en = (d.transpose(-1, -2) @ pred_aln_trg.unsqueeze(0).to(self.device))
            if self.model_params.decoder.type == "hifigan":
                asr_new = torch.zeros_like(en)
                asr_new[:, :, 0] = en[:, :, 0]
                asr_new[:, :, 1:] = en[:, :, 0:-1]
                en = asr_new

            F0_pred, N_pred = self.model.predictor.F0Ntrain(en, s)

            asr = (t_en @ pred_aln_trg.unsqueeze(0).to(self.device))
            if self.model_params.decoder.type == "hifigan":
                asr_new = torch.zeros_like(asr)
                asr_new[:, :, 0] = asr[:, :, 0]
                asr_new[:, :, 1:] = asr[:, :, 0:-1]
                asr = asr_new
            var = ref.squeeze().unsqueeze(0)

            out = self.model.decoder(asr,F0_pred, N_pred, var)

            #logging.info("here18")
        output = out.squeeze().cpu().numpy()[..., :-50] # weird pulse at the end of the model, need to be fixed later
        if output_wav_file:
            logging.info("Returing the output file")
            scipy.io.wavfile.write(output_wav_file, rate=output_sample_rate, data=output)
        return output

    def long_inference(self,
                       text: str,
                       target_voice_path=None,
                       output_wav_file=None,
                       output_sample_rate=24000,
                       alpha=0.3,
                       beta=0.7,
                       t=0.7,
                       diffusion_steps=5,
                       embedding_scale=1,
                       ref_s=None):

        if ref_s is None:
            if not target_voice_path or not Path(target_voice_path).exists():
                print("Cloning default target voice...")
                target_voice_path = cached_path(DEFAULT_TARGET_VOICE_URL)
            ref_s = self.compute_style(target_voice_path)  # target style vector

        text_segments = segment_text(text)
        segments = []
        prev_s = None
        for text_segment in text_segments:
            # Address cut-off sentence issue due to langchain text splitter
            if text_segment[-1] != '.':
                text_segment += ', '
            segment_output, prev_s = self.long_inference_segment(text_segment,
                                                                 prev_s,
                                                                 ref_s,
                                                                 alpha=alpha,
                                                                 beta=beta,
                                                                 t=t,
                                                                 diffusion_steps=diffusion_steps,
                                                                 embedding_scale=embedding_scale)
            segments.append(segment_output)
        output = np.concatenate(segments)
        if output_wav_file:
            scipy.io.wavfile.write(output_wav_file, rate=output_sample_rate, data=output)
        return output

    def long_inference_segment(self,
                               text,
                               prev_s,
                               ref_s,
                               alpha=0.3,
                               beta=0.7,
                               t=0.7,
                               diffusion_steps=5,
                               embedding_scale=1):
        
        text = text.strip()
        text = text.replace('"', '')
        phonemized_text = self.phoneme_converter.phonemize(text)
        ps = word_tokenize(phonemized_text)
        phoneme_string = ' '.join(ps)
        phoneme_string = phoneme_string.replace('``', '"')
        phoneme_string = phoneme_string.replace("''", '"')

        textcleaner = TextCleaner()
        tokens = textcleaner(phoneme_string)
        tokens.insert(0, 0)
        tokens = torch.LongTensor(tokens).to(self.device).unsqueeze(0)

        with torch.no_grad():
            input_lengths = torch.LongTensor([tokens.shape[-1]]).to(self.device)
            text_mask = length_to_mask(input_lengths).to(self.device)

            t_en = self.model.text_encoder(tokens, input_lengths, text_mask)
            bert_dur = self.model.bert(tokens, attention_mask=(~text_mask).int())
            d_en = self.model.bert_encoder(bert_dur).transpose(-1, -2)

            s_pred = self.sampler(noise = torch.randn((1, 256)).unsqueeze(1).to(self.device),
                                  embedding=bert_dur,
                                  embedding_scale=embedding_scale,
                                  features=ref_s, # reference from the same speaker as the embedding
                                  num_steps=diffusion_steps).squeeze(1)

            if prev_s is not None:
                # convex combination of previous and current style
                s_pred = t * prev_s + (1 - t) * s_pred

            s = s_pred[:, 128:]
            ref = s_pred[:, :128]

            ref = alpha * ref + (1 - alpha)  * ref_s[:, :128]
            s = beta * s + (1 - beta)  * ref_s[:, 128:]

            s_pred = torch.cat([ref, s], dim=-1)

            d = self.model.predictor.text_encoder(d_en,
                                             s, input_lengths, text_mask)

            x, _ = self.model.predictor.lstm(d)
            duration = self.model.predictor.duration_proj(x)

            duration = torch.sigmoid(duration).sum(axis=-1)
            pred_dur = torch.round(duration.squeeze()).clamp(min=1)


            pred_aln_trg = torch.zeros(input_lengths, int(pred_dur.sum().data))
            c_frame = 0
            for i in range(pred_aln_trg.size(0)):
                pred_aln_trg[i, c_frame:c_frame + int(pred_dur[i].data)] = 1
                c_frame += int(pred_dur[i].data)

            # encode prosody
            en = (d.transpose(-1, -2) @ pred_aln_trg.unsqueeze(0).to(self.device))
            if self.model_params.decoder.type == "hifigan":
                asr_new = torch.zeros_like(en)
                asr_new[:, :, 0] = en[:, :, 0]
                asr_new[:, :, 1:] = en[:, :, 0:-1]
                en = asr_new

            F0_pred, N_pred = self.model.predictor.F0Ntrain(en, s)

            asr = (t_en @ pred_aln_trg.unsqueeze(0).to(self.device))
            if self.model_params.decoder.type == "hifigan":
                asr_new = torch.zeros_like(asr)
                asr_new[:, :, 0] = asr[:, :, 0]
                asr_new[:, :, 1:] = asr[:, :, 0:-1]
                asr = asr_new

            out = self.model.decoder(asr,
                                F0_pred, N_pred, ref.squeeze().unsqueeze(0))

        return out.squeeze().cpu().numpy()[..., :-100], s_pred

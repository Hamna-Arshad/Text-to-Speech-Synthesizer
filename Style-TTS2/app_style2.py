from style2_tts.StyleTTS2 import tts_new  # Assuming your `StyleTTS2` class is in `tts_new.py`
import logging
import time
# Configure logging
logging.basicConfig(
    level=logging.INFO, # (works for all levels above debug: info, warning, error,critical)
    format='%(asctime)s - %(levelname)s - %(message)s', # time stamp, level name, message to be displayed
    filename='/home/hamna/Desktop/Internship-2024/tts.log', # file where log is saved
    filemode='w' # file created in write mode (overwrites existing file if present)
)

tts = None

def style_init():
    global tts
        # Initialize TTS model
    model_checkpoint_path = '/home/hamna/Desktop/Internship-2024/style2_tts/Models/LibriTTS/epochs_2nd_00020.pth'
    config_path = '/home/hamna/Desktop/Internship-2024/style2_tts/Models/LibriTTS/config.yml'

    logging.info("Creating the StyleTTS2 object")
    try:  
        tts = tts_new.StyleTTS2(model_checkpoint_path, config_path)
        logging.info("Object created")

        
    except Exception as e:
        logging.error(f"Error in loading the StyleTTS2 model{e}")


def style_model(text, voice):
    start = time.time()
    logging.info("Style TTS2 model called")
    global tts
    output_file = "/home/hamna/Desktop/Internship-2024/output.wav"
    if voice == "female_high":
        voice_path = "/home/hamna/Desktop/Internship-2024/style2_tts/StyleTTS2/Demo/reference_audio/female_high.wav"
    elif voice == "male_low":
        voice_path = "/home/hamna/Desktop/Internship-2024/style2_tts/StyleTTS2/Demo/reference_audio/male_low.wav"
    elif voice == "male_medium":
        voice_path = "/home/hamna/Desktop/Internship-2024/style2_tts/StyleTTS2/Demo/reference_audio/male_medium.wav"
    elif voice == "female_em":
        voice_path = "/home/hamna/Desktop/Internship-2024/style2_tts/StyleTTS2/Demo/reference_audio/female_em.wav"
    else:
        logging.error("Error in file path")
    try:

        logging.info("Calling the inference function")
        tts.inference(
            text,
            target_voice_path=voice_path,
            output_wav_file="/home/hamna/Desktop/Internship-2024/output.wav",
            output_sample_rate=24000,
            alpha=0.2,
            beta=0.8, 
            diffusion_steps=10,  
            embedding_scale=1.2 
        )
        logging.info("Inference function completed")
        end = time.time()-start
        logging.info("Total inference time is: "+ str(end)+" s")
        logging.info("\n\n")
    except Exception as e:
        logging.error(f"Error in conversion---hereee----{e}")    
    return output_file



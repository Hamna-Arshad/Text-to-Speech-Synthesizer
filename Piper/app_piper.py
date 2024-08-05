from flask import jsonify
import subprocess
import traceback
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, # (works for all levels above debug: info, warning, error,critical)
    format='%(asctime)s - %(levelname)s - %(message)s', # time stamp, level name, message to be displayed
    filename='/home/hamna/Desktop/Internship-2024/tts.log', # file where log is saved
    filemode='w' # file created in write mode (overwrites existing file if present)
)

  

   
def piper_model(text, voice):
            start = time.time()
            logging.info("Piper TTS model called")
        # Path to the Piper binary and model
            piper_binary = "/home/hamna/Desktop/Internship-2024/piper_tts/Libraries/piper"
            output_file = "/home/hamna/Desktop/Internship-2024/output.wav"

        #POST METHOD
            selected_voice = voice
            text_to_convert = text

            print("text is: ", text)
            print("voice is: ", voice)

            if not text_to_convert:
                logging.error("String not recieved")
            else:
                logging.info("Text recieved, proceeding to conversion")                   
        
            try:
                # Determine model path based on selected voice
                if selected_voice == "en_US-joe-medium":
                    model_path = "/home/hamna/Desktop/Internship-2024/piper_tts/voices/en_US-joe-medium.onnx"
                elif selected_voice == "en_US-danny-low":
                    model_path = "/home/hamna/Desktop/Internship-2024/piper_tts/voices/en_US-danny-low.onnx"
                elif selected_voice == "en_US-kathleen-low":
                    model_path = "/home/hamna/Desktop/Internship-2024/piper_tts/voices/en_US-kathleen-low.onnx"
                elif selected_voice == "en_GB-southern_english_female-low":
                    model_path = "/home/hamna/Desktop/Internship-2024/piper_tts/voices/en_GB-southern_english_female-low.onnx"
                else:
                    logging.error(f"Unknown voice selected: {selected_voice}")
                    return jsonify({'error': 'Unknown voice selected'}), 400
                
                logging.info(f"voice model selected: {selected_voice}")
                if not Path(model_path).exists():
                     print("model path is invalid")
                
                logging.info("Processing the input textual string")
                
                # Convert text to speech using Piper TTS
                subprocess.run(
                    [piper_binary, "-m", model_path, "-f", output_file],
                    input=text_to_convert.encode('utf-8'),  # encode textual string to 8 bit code (requirement to run subprocesses)
                    check=True  # for error checking, raises exception in case of if failure of subprocess call
                )
                logging.info("Conversion complete")
            
                # Return the audio file
                logging.info("Returning the generated audio to the webpage")
                end = time.time()-start
                logging.info("Total inference time is: "+ str(end)+" s")
                logging.info("\n\n")
                return output_file
            
            except subprocess.CalledProcessError as e:
                logging.error(f"Subprocess error: {e}")
                return jsonify({'error': f'Subprocess error: {str(e)}'}), 500

            except Exception as e:
                logging.error("Error converting text to speech --app_piper.py")
                logging.error(f"Error converting text to speech: {str(e)}")
                logging.error(traceback.format_exc()) 
                return jsonify({'error': f'Error converting text to speech(json): {str(e)}'}), 500

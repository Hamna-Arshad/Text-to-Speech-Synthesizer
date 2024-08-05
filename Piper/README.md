# Text-to-Speech Flask Application

This Flask application converts text input to speech using Piper TTS and serves the generated audio file.

## Prerequisites

Before running the application, ensure you have the following installed:

- Python 3.x
- Flask
- Werkzeug
- Piper TTS


## Installation
Follow the instructions to set up the working environment:

  1. Create a repository
  2. Install the dependencies

```bash
pip install -r requirements.txt
```
The requirements.txt includes:
- Flask==3.0.3
- Werkzeug==3.0.3


3. For installing piper use the following link:

- For Windows:
```bash
https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip
```
- For Linux:                                        
```bash
https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz
``` 
Install and unzip the folder

4. Install the voices:
Install both .onnx and .json files
- .onnx file:
```bash
https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/kathleen/low/en_US-kathleen-low.onnx?download=true
```
- .json file:
```bash
https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/kathleen/low/en_US-kathleen-low.onnx.json?download=true.json
```
Add both these files to the ./piper directory of the downloaded piper version.
## Usage

1. Run the Flask application:
- For Windows:
```bash
python your_python_file.py
```
- For Linux:
```bash
python3 your_python_file.py
```

2. Open your web browser and navigate to `http://localhost:55000/` to access the application.

- Change `55000` with the port number you are exposing.
3. Enter text in the provided form on the webpage and click "Convert".

4. The application will generate an audio file (`output.wav`) based on the text input.

## API Endpoints

- `/` - Homepage serving `index.html` for user interaction.
- `/convert` - POST endpoint for converting text to speech. Accepts `text` parameter.
- **Method:** POST
- **Parameters:** `text` (text to convert to speech)
- **Returns:** Audio file (`output.wav`) in WAV format.

## Logging

- Application logs are stored in `app-tts.log`.
- Log level is set to DEBUG, logging various stages of text-to-speech conversion.



# - Frontend  

The `index.html` file provides a simple web interface for the Text-to-Speech application. It includes a form where users can input text and submit it for conversion to speech.

### HTML Structure

- **Form**: Contains a textarea for inputting text and a submit button.
- **Audio Element**: Used to play the generated speech audio.

### JavaScript

The JavaScript function `submitForm(event)` handles form submission:

- **Prevent Default Submission**: Prevents the form from submitting normally to allow for an asynchronous request.
- **Fetch API**: Sends a POST request to the `/convert` endpoint with the form data.

**Response Handling**: 
- Converts the response to a Blob.
- Creates an object URL from the Blob and sets it as the source of the audio element.
- Plays the audio.


# - Docker Deployment

To run the application using Docker:
1. Build the Docker image:

```bash
docker build -t tts-app .
```

2. Run the Docker container:

```bash
docker run -d -p 55000:55000 --name container_name image_name
```
- Change the port number and image name according to your requirements.
- After running, open the local host at `http://localhost:55000/` to test your application. 

## Notes

- Ensure `piper_binary` and `model_path` are correctly configured in `app.py` for Piper TTS and ONNX model paths.
- Pygame integration (commented out in the code) allows for real-time audio playback but can be enabled if needed.
- Use `pip3` in place of `pip` in thr installation commands when working on linux.

### Useful docker commands:
#
- To enter docker container
```bash
docker exec -it container_name /bin/bash
```
- To list docker images
```bash
docker images
```
- To list docker containers
```bash
docker ps
```
- To stop docker container
```bash
docker stop container_name
```
- To remove a docker container
```bash
docker rm -f mcontainer_name
```
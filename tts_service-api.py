from flask import Flask, request, send_file, jsonify
from style2_tts import app_style2
from piper_tts import app_piper 
import flask.cli

app = Flask(__name__, static_folder="static")
 

if  flask.cli.is_running_from_reloader():
    print("loading from reloader")
    # Initializing the StyleTTS2 model
    app_style2.style_init()

@app.route('/')
def index():
    return app.send_static_file("index.html")


@app.route('/convert', methods=['POST'])
def convert():
    form_data = request.form
    model = form_data.get('model')
    voice = form_data.get('voice')
    text = form_data.get('text')


    if model == 'Piper-TTS':
        result = app_piper.piper_model(text, voice)
    elif model == 'Style-TTS':
        result = app_style2.style_model(text, voice)
    else:
        return jsonify({"error": "Invalid model selected"}), 400

    # Assuming `result` is the path to the generated audio file
    return send_file(result,  mimetype='audio/wav', as_attachment=False)

# Main function to run the Flask app
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=55000)    
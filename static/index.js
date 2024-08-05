    //model selection
document.addEventListener("DOMContentLoaded", function() {
    const modelDropdown = document.getElementById("model");

    modelDropdown.addEventListener("change", function() {
        const selectedModel = modelDropdown.value;
        if (selectedModel == "Style-TTS") {
            console.log("style selected");
            //disable the piper voices in dropdown
            var elements = document.getElementsByName("piper_voice");
            for (var i = 0; i < elements.length; i++) {
                elements[i].style.display = 'none';
            }
            elements = document.getElementsByName("style_voice");
            for (var i = 0; i < elements.length; i++) {
                elements[i].style.display = 'block';
            }
        } else {
            console.log("piper selected");
            var elements = document.getElementsByName("piper_voice");
            for (var i = 0; i < elements.length; i++) {
                elements[i].style.display = 'block';
            }
             elements = document.getElementsByName("style_voice");
            for (var i = 0; i < elements.length; i++) {
                elements[i].style.display = 'none';
            }
        }
    });

    // Initial check in case the dropdown has a pre-selected value
    const selectedModel = modelDropdown.value;
    if (selectedModel == "Style-TTS") {
        console.log("style selected");
        //disable the piper voice dropdown
    } else {
        console.log("piper selected");
        elements = document.getElementsByName("style_voice");
        for (var i = 0; i < elements.length; i++) {
            elements[i].style.display = 'none';
        }
    }
});




function submitForm(event) {
    event.preventDefault(); // Prevent the form from submitting normally

    const formData = new FormData(event.target);
    const voice = formData.get('voice'); // Get selected voice model
    const text = formData.get('text'); // Get entered text
    const model = formData.get('model'); // Get entered text

    fetch('/convert', {
        method: 'POST',
        body: formData
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Error converting text to speech');
            }
            return response.blob();
        })
        .then(blob => {
            const audioURL = URL.createObjectURL(blob);
            const audioElement = document.getElementById('audio');
            const sourceElement = document.getElementById('audioSource');
            sourceElement.src = audioURL;
            audioElement.load();
            audioElement.play();
        })
        .catch(error => {
            console.error('Error:', error);
        });
}


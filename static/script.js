function getSessionId() {
  const urlParams = new URLSearchParams(window.location.search);
  let sessionId = urlParams.get("session_id");
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    urlParams.set("session_id", sessionId);
    const newUrl = `${window.location.pathname}?${urlParams.toString()}`;
    window.history.replaceState({}, "", newUrl);
  }
  return sessionId;
}
const sessionId = getSessionId();

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

const generateBtn = document.getElementById('generateBtn');
const textInput = document.getElementById('textInput');
const voiceSelect = document.getElementById('voiceSelect');
const audioPlayer = document.getElementById('audioPlayer');

const recordBtn = document.getElementById('recordBtn');
const timerDisplay = document.getElementById('timer');
const uploadStatus = document.getElementById('uploadStatus');
const transcriptDisplay = document.getElementById('transcriptDisplay');

let mediaRecorder = null;
let audioChunks = [];
let recordingStartTime = 0;
let recordingInterval = null;

generateBtn.addEventListener('click', async () => {
  const text = textInput.value || '';
  const voiceId = voiceSelect.value || 'en-US-natalie';
  if (!text.trim()) {
    alert('Please enter some text to generate audio.');
    return;
  }

  generateBtn.disabled = true;
  generateBtn.textContent = 'Generating...';

  try {
    const response = await fetch('/generate-audio', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voiceId, format: 'mp3' })
    });

    if (!response.ok) {
      let errText = `TTS server error: ${response.status}`;
      try { const j = await response.json(); if (j && j.error) errText += ` - ${j.error}`; } catch(_) {}
      throw new Error(errText);
    }

    const data = await response.json();
    const audioUrl = data.audioFile || (data.audioUrls && data.audioUrls[0]) || data.audio_url || data.audio?.audioFile;

    if (!audioUrl) {
      throw new Error('No audio URL returned from TTS.');
    }

    audioPlayer.src = audioUrl;
    audioPlayer.onloadedmetadata = () => {
      audioPlayer.play().catch((e) => {
        console.warn('Autoplay blocked or failed:', e);
      });
    };

  } catch (err) {
    console.error('Generate audio failed:', err);
    alert('Text-to-speech failed: ' + (err.message || err));
  } finally {
    generateBtn.disabled = false;
    generateBtn.textContent = 'Generate & Play';
  }
});


function startRecording(stream) {
  audioChunks = [];
  mediaRecorder = new MediaRecorder(stream);
  uploadStatus.textContent = '';
  transcriptDisplay.textContent = '';

  mediaRecorder.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) audioChunks.push(e.data);
  };

  mediaRecorder.onstart = () => {
    recordingStartTime = Date.now();
    timerDisplay.textContent = 'Recording Time: 0s';
    timerDisplay.style.display = 'block';
    recordBtn.classList.add('recording');
    recordBtn.innerHTML = 'Stop Recording';

    recordingInterval = setInterval(() => {
      const elapsedSeconds = Math.floor((Date.now() - recordingStartTime) / 1000);
      timerDisplay.textContent = `Recording Time: ${elapsedSeconds}s`;
    }, 1000);
  };

  mediaRecorder.onstop = async () => {
    clearInterval(recordingInterval);
    timerDisplay.style.display = 'none';
    recordBtn.classList.remove('recording');
    recordBtn.innerHTML = 'Start Recording';

    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });

    try {
      const previewUrl = URL.createObjectURL(audioBlob);
    } catch (e) {
      console.warn('Preview creation failed:', e);
    }

    uploadStatus.style.color = ''; // reset color
    uploadStatus.textContent = 'Uploading recording...';
    try {
      const uploadForm = new FormData();
      uploadForm.append('audio', audioBlob, 'recording.webm');

      const uploadRes = await fetch('/upload-audio', {
        method: 'POST',
        body: uploadForm
      });

      if (!uploadRes.ok) {
        let errMsg = `Upload failed: ${uploadRes.status}`;
        try { const j = await uploadRes.json(); if (j && j.error) errMsg += ` - ${j.error}`; } catch(_) {}
        throw new Error(errMsg);
      }

      const uploadJson = await uploadRes.json();
      uploadStatus.style.color = 'var(--success)';
      uploadStatus.textContent = `Uploaded: ${uploadJson.filename || 'recording.webm'} (${uploadJson.content_type || 'n/a'}, ${uploadJson.size || 'n/a'} bytes)`;

      uploadStatus.textContent = 'Processing with AI assistant...';
      const agentForm = new FormData();
      agentForm.append('audio', audioBlob, 'recording.webm');

      const agentRes = await fetch(`/agent/chat/${sessionId}`, {
        method: 'POST',
        body: agentForm
      });

      if (!agentRes.ok) {
        let errMsg = `Agent processing failed: ${agentRes.status}`;
        try { const j = await agentRes.json(); if (j && j.error) errMsg += ` - ${j.error}`; } catch(_) {}
        throw new Error(errMsg);
      }

      const data = await agentRes.json();

      const youSaid = escapeHtml(data.transcribedText || '');
      const botReply = escapeHtml(data.llmText || '');

      transcriptDisplay.innerHTML = `You said: ${youSaid.replace(/\n/g, '<br>')}<br><br>Assistant: ${botReply.replace(/\n/g, '<br>')}`;

      const audioToPlay = (data.audioUrls && data.audioUrls.length > 0) ? data.audioUrls[0] : (data.audioFile || null);

      if (audioToPlay) {
        audioPlayer.src = audioToPlay;
        audioPlayer.onloadedmetadata = () => {
          audioPlayer.play().catch((err) => {
            console.warn('Playback failed:', err);
          });
        };
      } else {
        uploadStatus.textContent = 'Processed (no TTS url returned).';
      }

      uploadStatus.textContent = 'Done';

    } catch (err) {
      console.error('Recording upload/processing failed:', err);
      uploadStatus.style.color = 'var(--danger)';
      uploadStatus.textContent = `Error: ${err.message || err}`;
    } finally {
      audioChunks = [];
    }
  };

  mediaRecorder.start();
}

recordBtn.addEventListener('click', async () => {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    try {
      mediaRecorder.stop();
    } catch (e) {
      console.warn('Stop recording error:', e);
    }
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    startRecording(stream);
  } catch (err) {
    console.error('Could not start recording:', err);
    alert('Unable to access microphone. Please check permissions and try again.');
  }
});

(function initUI() {
  audioPlayer.style.display = 'none'; 
  timerDisplay.style.display = 'none';
  uploadStatus.textContent = '';
  transcriptDisplay.textContent = 'Say something and the assistant will reply here...';
  recordBtn.innerHTML = 'Start Recording';
})();

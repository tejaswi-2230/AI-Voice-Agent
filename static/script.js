// // Generate or retrieve session ID from URL or localStorage
// function getSessionId() {
//   const urlParams = new URLSearchParams(window.location.search);
//   let sessionId = urlParams.get("session_id");
//   if (!sessionId) {
//     sessionId = crypto.randomUUID();
//     urlParams.set("session_id", sessionId);
//     const newUrl = `${window.location.pathname}?${urlParams.toString()}`;
//     window.history.replaceState({}, "", newUrl);
//   }
//   return sessionId;
// }
// const sessionId = getSessionId();

// // Small helper to safely escape user / server text for innerHTML
// function escapeHtml(text) {
//   const div = document.createElement('div');
//   div.textContent = text;
//   return div.innerHTML;
// }

// // --- Text-to-Speech Logic ---
// document.getElementById('generateBtn').addEventListener('click', async () => {
//   const text = document.getElementById('textInput').value;
//   const voiceId = document.getElementById('voiceSelect').value;
//   const audioPlayer = document.getElementById('audioPlayer');

//   try {
//     const response = await fetch('/generate-audio', {
//       method: 'POST',
//       headers: { 'Content-Type': 'application/json' },
//       body: JSON.stringify({ text, voiceId })
//     });

//     if (!response.ok) {
//       throw new Error(`TTS server error: ${response.status}`);
//     }

//     const data = await response.json();

//     if (data.audioFile) {
//       audioPlayer.src = data.audioFile;
//       audioPlayer.style.display = 'block';
//       await audioPlayer.play().catch(() => {}); // ignore autoplay rejection
//     } else {
//       alert(data.error || 'Something went wrong!');
//     }
//   } catch (err) {
//     console.error("Generate audio failed:", err);
//     alert("Text-to-speech failed. Playing fallback audio.");
//     // show and play local fallback if available
//     const audioPlayer = document.getElementById('audioPlayer');
//     audioPlayer.src = "/static/fallback.mp3";
//     audioPlayer.style.display = 'block';
//     audioPlayer.play().catch(() => {});
//   }
// });

// // --- Echo Bot Logic ---
// let mediaRecorder;
// let audioChunks = [];

// const startBtn = document.getElementById('startBtn');
// const stopBtn = document.getElementById('stopBtn');
// const echoAudio = document.getElementById('echoAudio');
// const downloadBtn = document.getElementById('downloadBtn');
// const timerDisplay = document.getElementById('timer');
// const discardBtn = document.getElementById('discardBtn');
// const uploadStatus = document.getElementById('uploadStatus');
// const transcribeBtn = document.getElementById('transcribeBtn');
// const transcriptDisplay = document.getElementById('transcriptDisplay');

// let recordingStartTime = 0;
// let recordingInterval;
// let uploadComplete = false;

// transcribeBtn.disabled = true;

// startBtn.addEventListener('click', async () => {
//   try {
//     const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
//     mediaRecorder = new MediaRecorder(stream);
//     audioChunks = [];
//     uploadComplete = false;
//     transcribeBtn.disabled = true;

//     mediaRecorder.ondataavailable = (event) => {
//       audioChunks.push(event.data);
//     };

//     mediaRecorder.onstart = () => {
//       recordingStartTime = Date.now();
//       timerDisplay.textContent = 'Recording Time: 0s';
//       timerDisplay.style.display = 'block';
//       uploadStatus.style.display = 'none';
//       recordingInterval = setInterval(() => {
//         const elapsedSeconds = Math.floor((Date.now() - recordingStartTime) / 1000);
//         timerDisplay.textContent = `Recording Time: ${elapsedSeconds}s`;
//       }, 1000);
//     };

//     mediaRecorder.onstop = async () => {
//       clearInterval(recordingInterval);
//       timerDisplay.style.display = 'none';
//       const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
//       const audioURL = URL.createObjectURL(audioBlob);
//       echoAudio.src = audioURL;
//       echoAudio.style.display = 'block';
//       // play the raw recording for preview (ignore play rejection)
//       echoAudio.play().catch(() => {});

//       downloadBtn.style.display = 'inline-block';
//       discardBtn.style.display = 'inline-block';

//       uploadStatus.textContent = 'Ready to send...';
//       uploadStatus.style.display = 'block';

//       // keep upload step (you had this originally)
//       const formData = new FormData();
//       formData.append('audio', audioBlob, 'echo-recording.webm');

//       try {
//         const res = await fetch('/upload-audio', {
//           method: 'POST',
//           body: formData
//         });
//         const data = await res.json();

//         if (data.error) {
//           uploadStatus.textContent = `Upload failed: ${data.error}`;
//           uploadComplete = false;
//         } else {
//           uploadStatus.textContent = `Uploaded: ${data.filename} (${data.content_type || 'n/a'}, ${data.size || 'n/a'} bytes)`;
//           uploadComplete = true;
//           transcribeBtn.disabled = false;
//         }
//       } catch (err) {
//         uploadStatus.textContent = `Upload failed: ${err.message}`;
//         uploadComplete = false;
//       }

//       downloadBtn.onclick = () => {
//         const a = document.createElement('a');
//         a.href = audioURL;
//         a.download = 'echo-recording.webm';
//         a.click();
//       };
//     };

//     mediaRecorder.start();
//     startBtn.disabled = true;
//     stopBtn.disabled = false;
//     downloadBtn.style.display = 'none';
//     discardBtn.style.display = 'none';
//     uploadStatus.style.display = 'none';
//     transcriptDisplay.textContent = '';
//   } catch (err) {
//     console.error("Could not start recording:", err);
//     alert("Unable to access microphone. Please check permissions.");
//   }
// });

// stopBtn.addEventListener('click', () => {
//   if (mediaRecorder && mediaRecorder.state !== 'inactive') {
//     mediaRecorder.stop();
//   }
//   startBtn.disabled = false;
//   stopBtn.disabled = true;
// });

// discardBtn.addEventListener('click', () => {
//   echoAudio.src = '';
//   echoAudio.style.display = 'none';
//   downloadBtn.style.display = 'none';
//   discardBtn.style.display = 'none';
//   uploadStatus.style.display = 'none';
//   transcriptDisplay.textContent = '';
//   audioChunks = [];
//   uploadComplete = false;
//   transcribeBtn.disabled = true;
// });

// // --- Transcribe / Agent Chat (Day 11 error-handled) ---
// transcribeBtn.addEventListener('click', async () => {
//   if (!uploadComplete) {
//     transcriptDisplay.textContent = ' (Please wait for upload to finish)';
//     return;
//   }

//   if (!audioChunks || audioChunks.length === 0) {
//     transcriptDisplay.textContent = ' (No recording to process)';
//     return;
//   }

//   transcriptDisplay.textContent = ' (Processing with LLM + Murf voice...)';

//   const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
//   const formData = new FormData();
//   formData.append('audio', audioBlob, 'recording.webm');

//   try {
//     const response = await fetch(`/agent/chat/${sessionId}`, {
//       method: 'POST',
//       body: formData
//     });

//     if (!response.ok) {
//       // try to extract more info from JSON if possible
//       let errDetail = `Server error: ${response.status}`;
//       try {
//         const errJson = await response.json();
//         if (errJson && errJson.error) errDetail += ` - ${errJson.error}`;
//       } catch (_) {}
//       throw new Error(errDetail);
//     }

//     const data = await response.json();

//     // Display safe, escaped text (use innerHTML to preserve line breaks)
//     const youSaid = escapeHtml(data.transcribedText || '');
//     const botReply = escapeHtml(data.llmText || '');
//     transcriptDisplay.innerHTML = `You said: ${youSaid.replace(/\n/g, '<br>')}<br><br>LLM replied: ${botReply.replace(/\n/g, '<br>')}`;

//     // prefer server-provided audioUrls; fallback to local fallback.mp3 if missing
//     const audioToPlay = (data.audioUrls && data.audioUrls.length > 0) ? data.audioUrls[0] : "/static/fallback.mp3";

//     if (!audioToPlay) {
//       console.warn("No audio to play.");
//       return;
//     }

//     echoAudio.src = audioToPlay;
//     echoAudio.style.display = 'block';
//     // don't auto start recording when audio ends (as you requested earlier)
//     echoAudio.onended = null;

//     // Play and handle playback error by falling back to local file
//     echoAudio.play().catch((playErr) => {
//       console.warn("Playback failed, trying fallback static audio:", playErr);
//       echoAudio.src = "/static/fallback.mp3";
//       echoAudio.style.display = 'block';
//       echoAudio.play().catch(() => {
//         console.error("Fallback audio also failed.");
//       });
//     });

//   } catch (err) {
//     console.error("Request failed:", err);
//     transcriptDisplay.textContent = "(Error: Unable to connect or process request)";
//     // Try to play local fallback
//     echoAudio.src = "/static/fallback.mp3";
//     echoAudio.style.display = 'block';
//     echoAudio.play().catch(() => {});
//   }
// });

// Generate or retrieve session ID from URL or localStorage
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

// Small helper to safely escape user / server text for innerHTML
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// DOM elements
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

// --- Text-to-Speech Logic (left panel) ---
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
    // Accept different shapes: audioFile or audioUrls array or audioFile nested
    const audioUrl = data.audioFile || (data.audioUrls && data.audioUrls[0]) || data.audio_url || data.audio?.audioFile;

    if (!audioUrl) {
      throw new Error('No audio URL returned from TTS.');
    }

    // set hidden audio player and autoplay
    audioPlayer.src = audioUrl;
    // ensure player is ready to autoplay when metadata loaded
    audioPlayer.onloadedmetadata = () => {
      audioPlayer.play().catch((e) => {
        // Browsers may block autoplay — still set src so user can manually play if needed.
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

// --- Combined Start/Stop Recording Logic (right panel) ---
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

    // Show a small preview by creating a local URL (optional)
    try {
      const previewUrl = URL.createObjectURL(audioBlob);
      // we are intentionally not showing a visible audio UI - but keep preview for debug if needed
      // echo preview: (not displayed publicly)
      // echoAudio.src = previewUrl;
    } catch (e) {
      console.warn('Preview creation failed:', e);
    }

    // Upload the file to server (keep original step for storage)
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

      // Now automatically send to /agent/chat/<sessionId> for STT + LLM + TTS
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

      // Display transcribed and assistant text safely
      const youSaid = escapeHtml(data.transcribedText || '');
      const botReply = escapeHtml(data.llmText || '');

      transcriptDisplay.innerHTML = `You said: ${youSaid.replace(/\n/g, '<br>')}<br><br>Assistant: ${botReply.replace(/\n/g, '<br>')}`;

      // Determine audio to play: prefer audioUrls array or audioFile
      const audioToPlay = (data.audioUrls && data.audioUrls.length > 0) ? data.audioUrls[0] : (data.audioFile || null);

      if (audioToPlay) {
        audioPlayer.src = audioToPlay;
        // autoplay when ready
        audioPlayer.onloadedmetadata = () => {
          audioPlayer.play().catch((err) => {
            console.warn('Playback failed:', err);
            // do not fallback to local static audio as requested
          });
        };
      } else {
        // No TTS URL provided — still show assistant text
        uploadStatus.textContent = 'Processed (no TTS url returned).';
      }

      uploadStatus.textContent = 'Done';

    } catch (err) {
      console.error('Recording upload/processing failed:', err);
      uploadStatus.style.color = 'var(--danger)';
      uploadStatus.textContent = `Error: ${err.message || err}`;
    } finally {
      // cleanup chunks so next recording starts fresh
      audioChunks = [];
    }
  };

  mediaRecorder.start();
}

recordBtn.addEventListener('click', async () => {
  // Toggle behavior: if recording -> stop ; else start
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    try {
      mediaRecorder.stop();
    } catch (e) {
      console.warn('Stop recording error:', e);
    }
    return;
  }

  // Start new recording
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    startRecording(stream);
  } catch (err) {
    console.error('Could not start recording:', err);
    alert('Unable to access microphone. Please check permissions and try again.');
  }
});

// Ensure UI initial state is correct
(function initUI() {
  audioPlayer.style.display = 'none'; // hidden player (we will autoplay programmatically)
  timerDisplay.style.display = 'none';
  uploadStatus.textContent = '';
  transcriptDisplay.textContent = 'Say something and the assistant will reply here...';
  recordBtn.innerHTML = 'Start Recording';
})();

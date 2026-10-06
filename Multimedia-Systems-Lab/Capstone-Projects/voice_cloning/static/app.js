/**
 * Talking Tom: Ultra-Fast Voice Mimic
 */

// State
let isRecording = false;
let isPlaying = false;
let audioContext = null;
let analyser = null;
let micStream = null;
let micAnalyser = null;
let mediaRecorder = null;
let recordedChunks = [];
let recognition = null;
let currentTranscript = '';

// DOM Elements
const DOM = {
    tomViewport: document.getElementById('tomViewport'),
    bubbleTag: document.getElementById('bubbleTag'),
    bubbleContent: document.getElementById('bubbleContent'),
    mouthClosed: document.getElementById('mouthClosed'),
    mouthOpen: document.getElementById('mouthOpen'),
    mouthTongue: document.getElementById('mouthTongue'),
    leftEye: document.getElementById('leftEye'),
    rightEye: document.getElementById('rightEye'),
    avatarStatusText: document.getElementById('avatarStatusText'),
    waveformCanvas: document.getElementById('waveformCanvas'),
    btnMic: document.getElementById('btnMic'),
    micBtnTitle: document.getElementById('micBtnTitle'),
    micBtnSub: document.getElementById('micBtnSub')
};

// 1. AudioContext
function getAudioContext() {
    if (!audioContext) {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        audioContext = new AudioCtx({ latencyHint: 'interactive' });
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        analyser.smoothingTimeConstant = 0.5;
        analyser.connect(audioContext.destination);
    }
    if (audioContext.state === 'suspended') {
        audioContext.resume();
    }
    return audioContext;
}

// 2. Speech Recognition (Web Speech API)
function initSTT() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    try {
        const rec = new SpeechRecognition();
        rec.continuous = true;
        rec.interimResults = true;
        rec.lang = 'en-US';

        rec.onresult = (event) => {
            let transcript = '';
            for (let i = event.resultIndex; i < event.results.length; ++i) {
                transcript += event.results[i][0].transcript;
            }
            if (transcript.trim()) {
                currentTranscript = transcript.trim();
                DOM.bubbleTag.textContent = 'Tom heard:';
                DOM.bubbleContent.textContent = `"${currentTranscript}"`;
            }
        };

        rec.onerror = () => {};
        rec.onend = () => {
            if (isRecording) {
                try { rec.start(); } catch (e) {}
            }
        };

        recognition = rec;
    } catch (e) {
        console.warn('STT unavailable:', e);
    }
}

// 3. Microphone Recording
async function startRecording() {
    getAudioContext();
    isRecording = true;
    currentTranscript = '';
    recordedChunks = [];

    DOM.tomViewport.classList.add('listening');
    DOM.btnMic.classList.add('recording');
    DOM.micBtnTitle.textContent = '🔴 LISTENING...';
    DOM.micBtnSub.textContent = 'Tap again or release when done';
    DOM.avatarStatusText.textContent = 'Tom is listening to you...';

    try {
        if (!micStream) {
            micStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
            const micSource = audioContext.createMediaStreamSource(micStream);
            micAnalyser = audioContext.createAnalyser();
            micAnalyser.fftSize = 256;
            micSource.connect(micAnalyser);

            mediaRecorder = new MediaRecorder(micStream);
            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) recordedChunks.push(e.data);
            };
        }

        recordedChunks = [];
        if (mediaRecorder && mediaRecorder.state === 'inactive') {
            mediaRecorder.start(40);
        }

        if (recognition) {
            try { recognition.start(); } catch (e) {}
        }
    } catch (err) {
        console.error('Microphone error:', err);
        alert('Please allow microphone access to talk to Tom!');
        stopRecording();
    }
}

function stopRecording() {
    if (!isRecording) return;
    isRecording = false;

    DOM.tomViewport.classList.remove('listening');
    DOM.btnMic.classList.remove('recording');
    DOM.micBtnTitle.textContent = '🎙️ TAP OR HOLD TO TALK';
    DOM.micBtnSub.textContent = 'Speak a few words to hear Tom echo';
    DOM.avatarStatusText.textContent = 'Tom is mimicking...';

    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }
    if (recognition) {
        try { recognition.stop(); } catch (e) {}
    }
}

// 4. Instant Chipmunk Pitch Shift Echo (<30ms)
async function triggerTomEcho() {
    stopRecording();
    getAudioContext();
    isPlaying = true;

    let audioBuffer = null;
    if (recordedChunks.length > 0) {
        try {
            const blob = new Blob(recordedChunks, { type: 'audio/webm' });
            const arrayBuf = await blob.arrayBuffer();
            audioBuffer = await audioContext.decodeAudioData(arrayBuf);
        } catch (e) {
            audioBuffer = null;
        }
    }

    // Fallback if no audio recorded
    if (!audioBuffer) {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const utter = new SpeechSynthesisUtterance(currentTranscript || 'Hello there!');
            utter.pitch = 1.95; // Chipmunk
            utter.rate = 1.25;  // Speedy

            DOM.tomViewport.classList.add('speaking');
            DOM.avatarStatusText.textContent = 'Tom is talking!';

            utter.onend = () => { onSpeechEnd(); };
            window.speechSynthesis.speak(utter);
            return;
        }
    }

    if (audioBuffer) {
        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;

        // Signature Talking Tom DSP Pitch Shift (+8 semitones, 1.22x speed)
        const pitchSemitones = 8;
        const speed = 1.22;
        source.playbackRate.value = speed * Math.pow(2, pitchSemitones / 12);

        source.connect(analyser);

        DOM.tomViewport.classList.add('speaking');
        DOM.avatarStatusText.textContent = 'Tom is echoing in chipmunk voice!';

        source.onended = () => { onSpeechEnd(); };
        source.start(0);
    }
}

function onSpeechEnd() {
    isPlaying = false;
    DOM.tomViewport.classList.remove('speaking');
    DOM.mouthClosed.style.display = 'block';
    DOM.mouthOpen.style.display = 'none';
    DOM.mouthTongue.style.display = 'none';
    DOM.avatarStatusText.textContent = 'Tom is waiting for you...';
}

// 5. Visualizer & Lip-Sync Animation
function startVisualizer() {
    const canvas = DOM.waveformCanvas;
    const ctx = canvas.getContext('2d');

    // Random eye blinking
    setInterval(() => {
        if (!isPlaying && DOM.leftEye && DOM.rightEye) {
            DOM.leftEye.style.transform = 'scaleY(0.1)';
            DOM.rightEye.style.transform = 'scaleY(0.1)';
            DOM.leftEye.style.transformOrigin = '114px 140px';
            DOM.rightEye.style.transformOrigin = '186px 140px';
            setTimeout(() => {
                DOM.leftEye.style.transform = 'scaleY(1)';
                DOM.rightEye.style.transform = 'scaleY(1)';
            }, 120);
        }
    }, 3600);

    function draw() {
        requestAnimationFrame(draw);
        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        let activeAnalyser = isPlaying ? analyser : (isRecording ? micAnalyser : null);

        if (activeAnalyser) {
            const bufLen = activeAnalyser.frequencyBinCount;
            const data = new Uint8Array(bufLen);
            activeAnalyser.getByteFrequencyData(data);

            let sum = 0;
            for (let i = 0; i < bufLen; i++) sum += data[i];
            const avg = sum / bufLen;

            // Lip-Sync Mouth Opening
            if (isPlaying) {
                if (avg > 16) {
                    DOM.mouthClosed.style.display = 'none';
                    DOM.mouthOpen.style.display = 'block';
                    DOM.mouthTongue.style.display = 'block';
                    const scaleY = 1 + (avg / 65);
                    DOM.mouthOpen.style.transform = `scaleY(${Math.min(1.8, scaleY)})`;
                    DOM.mouthOpen.style.transformOrigin = '150px 195px';
                } else {
                    DOM.mouthClosed.style.display = 'block';
                    DOM.mouthOpen.style.display = 'none';
                    DOM.mouthTongue.style.display = 'none';
                }
            }

            // Frequency bars
            const barW = (w / bufLen) * 2.2;
            let x = 0;
            for (let i = 0; i < bufLen; i++) {
                const barH = (data[i] / 255) * h * 0.9;
                ctx.fillStyle = isRecording ? '#38ef7d' : '#00f2fe';
                ctx.fillRect(x, h - barH, barW - 1, barH);
                x += barW;
            }
        } else {
            // Idle line
            ctx.beginPath();
            ctx.moveTo(0, h / 2);
            ctx.lineTo(w, h / 2);
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
            ctx.lineWidth = 2;
            ctx.stroke();
        }
    }

    draw();
}

// 6. Event Handlers
function setupEvents() {
    let isHolding = false;

    // Mouse Press & Hold or Tap
    DOM.btnMic.addEventListener('mousedown', (e) => {
        e.preventDefault();
        isHolding = true;
        if (!isRecording) startRecording();
    });

    window.addEventListener('mouseup', () => {
        if (isHolding && isRecording) {
            isHolding = false;
            triggerTomEcho();
        }
    });

    // Touch Support
    DOM.btnMic.addEventListener('touchstart', (e) => {
        e.preventDefault();
        isHolding = true;
        if (!isRecording) startRecording();
    });

    DOM.btnMic.addEventListener('touchend', (e) => {
        e.preventDefault();
        if (isHolding && isRecording) {
            isHolding = false;
            triggerTomEcho();
        }
    });

    // Spacebar Support
    let spaceDown = false;
    window.addEventListener('keydown', (e) => {
        if (e.code === 'Space' && !spaceDown) {
            spaceDown = true;
            e.preventDefault();
            if (!isRecording) startRecording();
        }
    });

    window.addEventListener('keyup', (e) => {
        if (e.code === 'Space' && spaceDown) {
            spaceDown = false;
            e.preventDefault();
            if (isRecording) triggerTomEcho();
        }
    });
}

// 7. Initialization
window.addEventListener('DOMContentLoaded', () => {
    initSTT();
    startVisualizer();
    setupEvents();
});

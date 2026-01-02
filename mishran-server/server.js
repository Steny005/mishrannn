const http = require('http');
const { WebSocketServer } = require('ws');
const os = require('os');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const server = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('Mishran Server Running');
});
const wss = new WebSocketServer({ server });

let clients = new Map();
let hostSocket = null; // Will store { socket, ffmpeg: null }
let currentSessionId = null;

// Ensure recordings directory exists
const recordingsDir = path.join(__dirname, 'recordings');
if (!fs.existsSync(recordingsDir)) {
    fs.mkdirSync(recordingsDir);
}

wss.on('connection', (socket, req) => {
    const clientId = req.url.split('/').pop();

    if (clientId === 'host_monitor') {
        hostSocket = { socket: socket, ffmpeg: null };
        console.log('✅ Host monitor connected');
        sendHostUpdate();

        socket.on('message', (message, isBinary) => {
            if (isBinary) {
                // Binary audio data from host
                if (hostSocket && hostSocket.ffmpeg && !hostSocket.ffmpeg.killed && hostSocket.ffmpeg.stdin.writable) {
                    hostSocket.ffmpeg.stdin.write(message, (err) => {
                        if (err) console.error(`[HOST WRITE ERROR]:`, err);
                    });
                }
            } else {
                try {
                    const data = JSON.parse(message);
                    console.log(`[HOST COMMAND]: Received command: ${data.command}`);
                    if (data.command === 'start_all') startAllRecording();
                    if (data.command === 'stop_all') stopAllRecording();
                } catch (error) {
                    // Ignore non-JSON text
                }
            }
        });

        socket.on('close', () => {
            console.log('❌ Host monitor disconnected');
            if (hostSocket) {
                stopFfmpeg(hostSocket, 'host_audio');
            }
            hostSocket = null;
        });

    } else { // This is a camera client
        console.log(`✅ Client ${clientId} connected`);
        clients.set(clientId, { socket, isRecording: false, ffmpeg: null });
        sendHostUpdate();

        socket.on('message', (message, isBinary) => {
            const client = clients.get(clientId);
            if (!client) return;

            if (isBinary) {
                // Binary video data from client
                if (client.isRecording && client.ffmpeg && !client.ffmpeg.killed && client.ffmpeg.stdin.writable) {
                    client.ffmpeg.stdin.write(message, (err) => {
                        if (err) console.error(`[CLIENT WRITE ERROR] [${clientId}]:`, err);
                    });
                }
            } else {
                try {
                    const data = JSON.parse(message);
                    if (data.type === 'recording_fully_stopped') {
                        console.log(`[CLIENT INFO]: Client ${clientId} confirmed recording fully stopped.`);
                        client.isRecording = false;
                        stopFfmpeg(client, clientId);
                        sendHostUpdate();
                    }
                } catch (error) {
                    // Ignore non-JSON text
                }
            }
        });

        socket.on('close', () => {
            console.log(`❌ Client ${clientId} disconnected`);
            const client = clients.get(clientId);
            if (client) {
                stopFfmpeg(client, clientId);
            }
            clients.delete(clientId);
            sendHostUpdate();
        });
    }
});

function startFfmpeg(target, id) {
    if (target.ffmpeg) return;

    if (!currentSessionId) {
        currentSessionId = Date.now();
    }

    const fileName = path.join(recordingsDir, `recording_${currentSessionId}_${id}.mkv`);
    console.log(`[FFMPEG]: Starting recording for ${id}`);
    console.log(`[FFMPEG]: Saving to file: ${fileName}`);

    // Goodies from root server.js: 
    // -f webm (input format)
    // -c copy (direct stream copy)
    // -movflags frag_keyframe+empty_moov (fix for abrupt stops)
    const args = [
        '-y',
        '-i', 'pipe:0'
    ];

    // Check if this is a video client (not host audio)
    if (id !== 'host_audio') {
        // Re-encode and rotate 90 degrees clockwise to force landscape
        args.push(
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-vf', 'transpose=1',
            '-c:a', 'copy'
        );
    } else {
        args.push('-c', 'copy');
    }

    args.push(fileName);

    const ffmpeg = spawn('ffmpeg', args);

    // Handle stdin errors (like EPIPE) to prevent server crash
    ffmpeg.stdin.on('error', (err) => {
        if (err.code !== 'EPIPE') {
             console.error(`[FFMPEG STDIN ERROR] [${id}]:`, err);
        }
    });

    ffmpeg.stderr.on('data', (data) => {
        // Uncomment for debug
        console.log(`FFmpeg [${id}]: ${data}`);
    });

    ffmpeg.on('close', (code) => {
        fs.stat(fileName, (err, stats) => {
            if (!err) {
                const sizeMB = (stats.size / (1024 * 1024)).toFixed(2);
                console.log(`[FFMPEG]: Recording saved: ${fileName} (${sizeMB} MB) (Exit code: ${code})`);
            } else {
                console.log(`[FFMPEG]: Recording saved: ${fileName} (Size unknown) (Exit code: ${code})`);
            }
        });
    });

    ffmpeg.on('error', (err) => {
        console.error(`[FFMPEG]: Error for ${id}:`, err);
    });

    target.ffmpeg = ffmpeg;
}

function stopFfmpeg(target, id) {
    if (target && target.ffmpeg) {
        console.log(`[FFMPEG]: Stopping recording for ${id}`);
        target.ffmpeg.stdin.end();
        target.ffmpeg = null;
    }
}

function startAllRecording() {
    console.log('\n[SERVER ACTION]: Command received: Start all recordings');
    currentSessionId = Date.now();

    if (hostSocket) {
        startFfmpeg(hostSocket, 'host_audio');
    }

    clients.forEach((client, clientId) => {
        if (!client.isRecording) {
            startFfmpeg(client, clientId);
            client.isRecording = true;
            client.socket.send(JSON.stringify({ command: 'start_recording' }));
        }
    });
    sendHostUpdate();
}

function stopAllRecording() {
    console.log('\n[SERVER ACTION]: Command received: Stop all recordings');

    if (hostSocket) {
        stopFfmpeg(hostSocket, 'host_audio');
    }

    clients.forEach((client, clientId) => {
        if (client.isRecording) {
            console.log(`[CLIENT VIDEO]: Sending stop command to client ${clientId}`);
            client.socket.send(JSON.stringify({ command: 'stop_recording' }));
        }
    });
}

function sendHostUpdate() {
    if (!hostSocket) return;
    const clientList = Array.from(clients.keys()).map(clientId => ({
        clientId,
        isRecording: clients.get(clientId).isRecording
    }));
    const isRecordingAll = clientList.length > 0 && clientList.every(client => client.isRecording);
    hostSocket.socket.send(JSON.stringify({
        type: 'state_update',
        isRecordingAll,
        clients: clientList
    }));
}

function getLocalIP() {
    const interfaces = os.networkInterfaces();
    for (const name of Object.keys(interfaces)) {
        for (const iface of interfaces[name]) {
            if (iface.family === 'IPv4' && !iface.internal) return iface.address;
        }
    }
    return 'localhost';
}

const PORT = 8080;
server.listen(PORT, '0.0.0.0', () => {
    const ip = getLocalIP();
    console.log(`\n🚀 WebSocket server running on port ${PORT}`);
    console.log(`   Connect clients to: ws://${ip}:${PORT}`);
});

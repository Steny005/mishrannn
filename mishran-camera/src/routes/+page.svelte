<script>
import CompactDisk from './cd.svelte';
import { onMount, onDestroy } from 'svelte';

// Constants for cleaner code
const KEYPAD_ROWS = [
	['1', '2', '3'],
	['4', '5', '6'],
	['7', '8', '9'],
	['.', '0', 'C']
];

const PAGES = {
	IP_INPUT: 0,
	CAMERA_VIEW: 1
};

// Reactive state
let pageState = $state(PAGES.IP_INPUT);
let cameraViewStatus = $state('CONNECTED');

// Core variables (keeping the original structure)
let camera = null;
let socket = null;
let recorder = null;
let videoElement;
let ipAddress = $state('');
let status = $state('Ready to connect');
let isConnecting = $state(false);

// Handle dialer input
function handleKeyPress(key) {
	if (key === 'C') {
		ipAddress = '';
	} else if (key === 'N') {
		connect();
	} else {
		ipAddress += key;
	}
}

async function connect() {
	const serverAddress = ipAddress.trim();
	if (!serverAddress) {
		alert('Please enter the server IP address and port.');
		return;
	}
	
	isConnecting = true;
	status = 'Initializing camera...';
	
	try {
		camera = await navigator.mediaDevices.getUserMedia({ 
			video: true, 
			audio: true 
		});
		
		// ✅ --- THIS IS THE DEBUGGING CODE --- ✅
		// It will print out all the media tracks your app receives.
		console.log("Inspecting tracks in the media stream:");
		camera.getTracks().forEach(track => {
			console.log(`- Found track: kind=${track.kind}, label=${track.label}`);
		});
		// ✅ ------------------------------------ ✅
		
		videoElement.srcObject = camera;
	} catch (err) {
		console.error("getUserMedia error:", err);
		status = 'Error: Could not access camera. Please grant permission.';
		isConnecting = false;
		return;
	}
	
	videoElement.onloadedmetadata = () => {
		const clientId = 'client_' + Math.floor(Math.random() * 10000);
		const wsUrl = `ws://${serverAddress}/${clientId}`;
		
		socket = new WebSocket(wsUrl);
		
		socket.onopen = () => {
			status = 'Connected';
			isConnecting = false;
			pageState = PAGES.CAMERA_VIEW; // Switch to camera view
		};
		
		socket.onmessage = (event) => {
			const message = JSON.parse(event.data);
			if (message.command === 'start_recording') {
				startRecording();
				cameraViewStatus = 'LIVE';
			}
			if (message.command === 'stop_recording') {
				stopRecording();
				cameraViewStatus = 'CONNECTED';
			}
		};
		
		socket.onclose = () => {
			status = 'Disconnected. Ready to connect.';
			isConnecting = false;
		};
		
		socket.onerror = (err) => {
			console.error("WebSocket Error:", err);
			status = 'Connection Failed.';
			isConnecting = false;
		};
	};
}

function startRecording() {
	if (recorder && recorder.state === 'recording') {
		return;
	}
	status = 'Recording...';
	if (!camera) return;
	
	recorder = new MediaRecorder(camera, { mimeType: 'video/webm' });
	
	recorder.ondataavailable = (event) => {
		if (event.data && event.data.size > 0) {
			socket.send(event.data);
		}
	};
	
	recorder.onstart = () => {
		console.log('MediaRecorder has started.');
	};
	
	recorder.onstop = () => {
		console.log("MediaRecorder has stopped. Notifying server.");
		status = 'Connected'; // Update the UI status
		if (socket && socket.readyState === WebSocket.OPEN) {
			socket.send(JSON.stringify({ type: 'recording_fully_stopped' }));
		}
	};
	
	recorder.start(1000);
}

function stopRecording() {
	if (recorder && recorder.state === 'recording') {
		recorder.stop();
	}
}

onDestroy(() => {
	if (camera) {
		camera.getTracks().forEach(track => track.stop());
	}
	if (socket) {
		socket.close();
	}
});
</script>

<main>
	<CompactDisk />

	{#if pageState === PAGES.IP_INPUT}
		<div class="placeholder" ></div>
		<div class="contents">
			<h1>{ipAddress || 'IP ADDRESS'}</h1>
			<div class="matrix">
				{#each KEYPAD_ROWS as row}
					<div class="matrix__row">
						{#each row as key}
							<div class="matrix__column" onclick={() => handleKeyPress(key)}>
								<p>{key}</p>
							</div>
						{/each}
					</div>
				{/each}
				<div class="matrix__row">
					<div class="matrix__column" onclick={() => handleKeyPress('N')}>
						<p>N</p>
					</div>
				</div>
			</div>
		</div>
	{:else if pageState === PAGES.CAMERA_VIEW}
		<div class="placeholder" ></div>
		<div class="contents">
			<h1>{cameraViewStatus}</h1>
			<div class="img">
				<img src="/tablet.png" alt="Device Frame" />
				<video class="video-feed" bind:this={videoElement} autoplay playsinline muted ></video>
			</div>
		</div>
	{/if}
</main>

<style>
	main {
		background: #ff3434;
		height: 100vh;
		display: flex;
		color: white;
		flex-direction: column;
		position: relative;
		z-index: 10;
		overflow: hidden; /* Prevents scrollbars */
	}
	.placeholder {
		flex: 1;
	}
	.contents {
		margin-inline: 2rem;
	}
	.contents h1 {
		text-align: center;
		font-size: 1rem;
		font-weight: 700;
		margin-bottom: 1rem;
		min-height: 1.2rem; /* Prevents layout shift when text changes */
	}

	/* Styles from Addr component */
	.matrix {
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
		margin: 0 1rem;
	}
	.matrix__row {
		display: flex;
		width: 100%;
		justify-content: space-between;
		margin-block: 1.25rem;
	}
	.matrix__row:last-child {
		justify-content: center;
	}
	.matrix__row:last-child .matrix__column p {
		color: white;
		filter: opacity(1);
	}
	.matrix__column {
		padding: 1rem;
		cursor: pointer;
		user-select: none; /* Prevents text selection on click */
		transition: transform 0.1s ease;
	}
	.matrix__column:active {
		transform: scale(0.9); /* Click feedback */
	}
	.matrix__column p {
		font-weight: 700;
		color: white;
		filter: opacity(0.4);
		font-size: 1.25rem;
	}

	/* Styles from Camera component */
	.img {
		position: relative; /* Needed to position the video inside */
		width: 80vw;
		margin: auto;
		margin-bottom: 2rem;
		display: flex;
		justify-content: center;
		align-items: center;
	}
	.img img {
		width: 100%;
		height: 100%;
	}

	.video-feed {
		position: absolute;
		/* These values are a starting point, adjust them to fit your tablet.png perfectly */
		width: 95%;
		height: 90%;
		object-fit: cover; /* Ensures video fills the space without distortion */
		border-radius: 20px; /* Optional: to match rounded corners */
	}
</style>
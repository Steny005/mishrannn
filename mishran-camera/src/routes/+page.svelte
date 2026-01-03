<script>
import CompactDisk from './cd.svelte';
import { onMount, onDestroy, tick } from 'svelte';
import { StatusBar } from '@capacitor/status-bar';
import { App } from '@capacitor/app';
import { Camera } from '@capacitor/camera';
import { ScreenOrientation } from '@capacitor/screen-orientation';

import { Capacitor } from '@capacitor/core';

const PAGES = {
	IP_INPUT: 0,
	CAMERA_VIEW: 1
};

// Reactive state
let pageState = $state(PAGES.IP_INPUT);
let cameraViewStatus = $state('CONNECTED');

onMount(async () => {
	if (Capacitor.isNativePlatform()) {
		try {
			await StatusBar.setOverlaysWebView({ overlay: true });
			await StatusBar.hide();
		} catch (error) {
			console.error('Error setting up environment:', error);
		}

		App.addListener('backButton', () => {
			if (pageState === PAGES.CAMERA_VIEW) {
				disconnectAndReset();
			} else {
				App.exitApp();
			}
		});
	}
});

function disconnectAndReset() {
	if (camera) {
		camera.getTracks().forEach(track => track.stop());
		camera = null;
	}
	if (socket) {
		socket.close();
		socket = null;
	}
	pageState = PAGES.IP_INPUT;
	status = 'Ready to connect';
}

// Core variables (keeping the original structure)
let camera = null;
let socket = null;
let recorder = null;
let videoElement;
// Default IP set to Cloudflare domain
let ipAddress = $state('gcp.laddu.cc');
let status = $state('Ready to connect');
let isConnecting = $state(false);

async function connect() {
	const serverAddress = ipAddress.trim();
	if (!serverAddress) {
		alert('Please enter the server address.');
		return;
	}
	
	isConnecting = true;
	status = 'Initializing camera...';
	
	try {
		// Request permissions explicitly for Android
		await Camera.requestPermissions();

		camera = await navigator.mediaDevices.getUserMedia({ 
			video: {
				facingMode: 'environment',
				width: { ideal: 1280 },
				height: { ideal: 720 },
				aspectRatio: { ideal: 1.7777777778 }
			}, 
			audio: true 
		});
		
		console.log("Camera access granted.");

		const clientId = 'client_' + Math.floor(Math.random() * 10000);
		const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
		const wsUrl = `${protocol}://${serverAddress}/${clientId}`;
		
		socket = new WebSocket(wsUrl);
		
		socket.onopen = async () => {
			status = 'Connected';
			pageState = PAGES.CAMERA_VIEW; // Switch to camera view
			
			// Wait for DOM to update so videoElement is available
			await tick();
			
			if (videoElement && camera) {
				videoElement.srcObject = camera;
			}
			isConnecting = false;
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
			pageState = PAGES.IP_INPUT; // Go back to start if disconnected
		};
		
		socket.onerror = (err) => {
			console.error("WebSocket Error:", err);
			status = 'Connection Failed.';
			isConnecting = false;
			alert('Connection failed. Check server address.');
		};

	} catch (err) {
		console.error("Setup error:", err);
		status = 'Error: ' + err.message;
		isConnecting = false;
		alert('Error connecting: ' + err.message);
		return;
	}
}

function startRecording() {
	if (recorder && recorder.state === 'recording') {
		return;
	}
	status = 'Recording...';
	if (!camera) return;
	
	recorder = new MediaRecorder(camera, { 
		mimeType: 'video/webm',
		videoBitsPerSecond: 10000000 // 10 Mbps for good balance
	});
	
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
		cameraViewStatus = 'CONNECTED'; 
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

			<div class="placeholder">
			</div>

			<div class="content">
				<h1>ready</h1>
			</div>

			<div class="placeholder">
			</div>

			<div class="contents">

				<div class="placeholder__action">

					<button class="btn--white" onclick={connect} disabled={isConnecting}>

						{#if isConnecting}

							CONNECTING...

								

						{:else}

							CONNECT

						{/if}

					</button>

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

	.placeholder__action {
		margin-bottom: 2rem;
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

	.content h1 {
		font-size: 1rem;
		font-weight: 700;
		text-align: center;
		text-transform: uppercase;
	}
</style>
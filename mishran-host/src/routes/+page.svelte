<script>
	import { onDestroy, onMount } from 'svelte';
	import CompactDisc from './cd.svelte';
	import { StatusBar } from '@capacitor/status-bar';
	import { App } from '@capacitor/app';

	import { Capacitor } from '@capacitor/core';

	onMount(async () => {
		if (Capacitor.isNativePlatform()) {
			try {
				await StatusBar.hide();
			} catch (error) {
				console.error('Error hiding status bar:', error);
			}

			App.addListener('backButton', () => {
				if (page === 2) {
					stopRecording();
				} else if (page === 1) {
					if (socket) socket.close();
					resetControls();
					page = 0;
				} else if (page > 2) {
					resetToHome();
				} else {
					App.exitApp();
				}
			});
		}
	});

	/**
	 * Page States:
	 * 0: Disconnected
	 * 1: Connected (Ready to Record)
	 * 2: Recording Active
	 * 3: Session Ended (Ready to Generate)
	 * 4: Processing (AI/Merging)
	 * 5: Complete (Download)
	 */
	let page = $state(0);
	
	// WebSocket & UI State
	let serverAddress = $state('');
	let status = $state('Enter server address to connect.');
	let clients = $state([]);
	let socket = $state(null);
	let isConnected = $state(false);
	let isConnecting = $state(false);
	let statusText = $state("");

	// Host Audio Recording State
	let hostAudioStream = $state(null);
	let hostRecorder = $state(null);

	$effect(() => {
		if (!isConnected && !isConnecting && page !== 0) {
			page = 0;
		}
	});

	const initiateConnection = () => {
		const address = 'gcp.laddu.cc';
		serverAddress = address;
		connect(serverAddress);
	};

	const connect = (address) => {
		status = `Connecting to ${address}...`;
		isConnecting = true;
		const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
		socket = new WebSocket(`${protocol}://${address}/host_monitor`);

		socket.onopen = () => {
			status = '✅ Connected to server';
			isConnected = true;
			isConnecting = false;
			page = 1;
		};

		socket.onmessage = (event) => {
			const data = JSON.parse(event.data);
			if (data.type === 'state_update') {
				clients = data.clients;
				statusText = data.statusText || "";
				
				// Sync server processing state to UI
				if (data.isProcessing && page !== 4) {
					page = 4;
				} else if (!data.isProcessing && page === 4) {
					page = 5;
				}
			}
		};

		socket.onclose = () => {
			status = '❌ Disconnected. Please reconnect';
			resetControls();
		};

		socket.onerror = (err) => {
			console.error('WebSocket error:', err);
			status = 'Error connecting. Check the address and ensure the server is running';
			resetControls();
		};
	};

	const resetControls = () => {
		isConnected = false;
		isConnecting = false;
		page = 0;
		clients = [];
	};

	const sendCommand = (command) => {
		if (socket && socket.readyState === WebSocket.OPEN) {
			console.log(`[DEBUG] Sending command: ${command}`);
			socket.send(JSON.stringify({ command }));
		}
	};

	const startRecording = async () => {
		try {
			hostAudioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
		} catch (err) {
			alert('Could not access microphone.');
			return;
		}

		const mimeTypes = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus'];
		const supportedMimeType = mimeTypes.find(type => MediaRecorder.isTypeSupported(type));

		if (!supportedMimeType) {
			hostAudioStream.getTracks().forEach(track => track.stop());
			return;
		}

		hostRecorder = new MediaRecorder(hostAudioStream, { mimeType: supportedMimeType });
		hostRecorder.ondataavailable = (event) => {
			if (event.data.size > 0 && socket && socket.readyState === WebSocket.OPEN) {
				socket.send(event.data);
			}
		};

		hostRecorder.onstart = () => {
			sendCommand('start_all');
			page = 2; 
		};

		hostRecorder.onstop = () => {
			hostAudioStream?.getTracks().forEach(track => track.stop());
			hostAudioStream = null;
			hostRecorder = null;
		};

		hostRecorder.start(1000);
	};

	const stopRecording = () => {
		sendCommand('stop_all');
		if (hostRecorder && hostRecorder.state === 'recording') {
			hostRecorder.stop();
		}
		page = 3; // Manually transition to post-session screen
	};

	const triggerPipeline = () => {
		sendCommand('start_pipeline');
		page = 4;
	};

	const downloadOutput = () => {
		const protocol = window.location.protocol; // 'http:' or 'https:'
		const downloadUrl = `${protocol}//${serverAddress}/download`;
		window.open(downloadUrl, '_blank');
	};

	const resetToHome = () => {
		page = 1;
		statusText = "";
	};

	onDestroy(() => {
		if (socket) socket.close();
		if (hostRecorder && hostRecorder.state === 'recording') hostRecorder.stop();
		else if (hostAudioStream) hostAudioStream.getTracks().forEach(track => track.stop());
	});
</script>

<main class:recording-active={page === 2}>
	<CompactDisc />


	{#if page === 0}
		<div class="page-container">
			<div class="placeholder"></div>

			<div class="content">
				<h1>ready</h1>
			</div>

			<div class="placeholder">
			</div>
			<div class="placeholder__action">
				<button class="btn--white" onclick={initiateConnection} disabled={isConnecting}>
					{isConnecting ? 'CONNECTING...' : 'CONNECT'}
				</button>
			</div>
		</div>
	{:else if page === 1}
		<div class="page-container">
			<div class="placeholder"></div>
			<div class="content">
				<h1>CONNECTED</h1>
				<div class="content__devices">
					{#each Array(4) as _, i}
						<img src="/tablet-android.svg" class:inactive={clients.length <= i} alt="Device {i + 1}" />
					{/each}
				</div>
			</div>
			<div class="placeholder">
				<div class="placeholder__action">
					<button class="btn--white" onclick={startRecording}>RECORD</button>
				</div>
			</div>
		</div>
	{:else if page === 2}
		<div class="page-container">
			<div class="placeholder"></div>
			<div class="content">
				<h1>RECORDING</h1>
			</div>
			<div class="placeholder">
				<div class="placeholder__action">
					<button class="btn--outline" onclick={stopRecording}>STOP</button>
				</div>
			</div>
		</div>
	{:else if page === 3}
		<div class="page-container">
			<div class="placeholder"></div>
			<div class="content">
				<h1>SESSION ENDED</h1>
			</div>
			<div class="placeholder">
				<div class="placeholder__action">
					<button class="btn--white" onclick={triggerPipeline}>GENERATE VIDEO</button>
					<button class="btn--outline" onclick={resetToHome} style="margin-top: 1rem;">CANCEL</button>
				</div>
			</div>
		</div>
	{:else if page === 4}
		<div class="page-container">
			<div class="placeholder"></div>
			<div class="content">
				<h1>{statusText || 'PROCESSING...'}</h1>
			</div>
			<div class="placeholder">
				<div class="placeholder__action">
					<button class="btn--outline" disabled>PLEASE WAIT</button>
				</div>
			</div>
		</div>
	{:else if page === 5}
		<div class="page-container">
			<div class="placeholder"></div>
			<div class="content">
				<h1>COMPLETE</h1>
			</div>
			<div class="placeholder">
				<div class="placeholder__action">
					<button class="btn--white" onclick={downloadOutput}>DOWNLOAD</button>
					<button class="btn--outline" onclick={resetToHome} style="margin-top: 1rem;">DONE</button>
				</div>
			</div>
		</div>
	{/if}
</main>

<style>
	main {
		background: black;
		height: 100vh;
		color: white;
		display: flex;
		flex-direction: column;
	}
	main.recording-active { background: #ff3434; }
	.page-container { height: 100%; display: flex; flex-direction: column; }
	.placeholder { flex: 1; }
	.placeholder:last-child { display: flex; align-items: flex-end; }
	.placeholder__action { margin-bottom: 2rem; width: 100%; padding-inline: 2rem; }
	.content h1 { text-align: center; font-size: 1rem; font-weight: 700; margin-bottom: 1rem; }
	.content__devices { display: flex; justify-content: center; align-items: center; margin-top: 1rem; }
	.content__devices img {
		margin-inline: 0.1rem; height: 1.5rem;
		filter: brightness(0) saturate(100%) invert(100%) sepia(6%) saturate(144%) hue-rotate(230deg) brightness(119%) contrast(100%);
	}
	.content__devices img.inactive { opacity: 0.4; }
	.content h1 {
		font-size: 1rem;
		font-weight: 700;
		text-align: center;
		text-transform: uppercase;
	}
</style>

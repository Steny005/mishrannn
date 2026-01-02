<script>
	import { onDestroy, onMount } from 'svelte';
	import CompactDisc from './cd.svelte';
	import { StatusBar } from '@capacitor/status-bar';
	import { App } from '@capacitor/app';

	onMount(async () => {
		try {
			await StatusBar.hide();
		} catch (error) {
			console.error('Error hiding status bar:', error);
		}

		App.addListener('backButton', () => {
			if (page === 2) {
				stopRecording();
			} else if (page === 1) {
				if (socket) {
					socket.close();
				}
				resetControls();
				page = 0;
			} else {
				App.exitApp();
			}
		});
	});

	// UI State
	let page = $state(0);
	let serverAddressDisplay = $state('CONNECT TO SERVER');
	
	// WebSocket State
	let serverAddress = $state('');
	let status = $state('Enter server address to connect.');
	let clients = $state([]);
	let socket = $state(null);
	let isConnected = $state(false);
	let isConnecting = $state(false);

	// Host Audio Recording State
	let hostAudioStream = $state(null);
	let hostRecorder = $state(null);

	$effect(() => {
		if (!isConnected && !isConnecting && page !== 0) {
			page = 0;
		}
	});

	const initiateConnection = () => {
		// Defaulting to 172.19.70.28:8080
		const address = '172.19.70.28:8080';
		serverAddress = address;
		connect(serverAddress);
	};

	const connect = (address) => {
		status = `Connecting to ${address}...`;
		isConnecting = true;
		socket = new WebSocket(`ws://${address}/host_monitor`);

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
		clients = [];
	};

	const sendCommand = (command) => {
		if (socket && socket.readyState === WebSocket.OPEN) {
			console.log(`[DEBUG] Sending command: ${command}`);
			socket.send(JSON.stringify({ command }));
		} else {
			console.error(`[DEBUG] FAILED to send command '${command}'. Socket state was: ${socket?.readyState}`);
		}
	};

	const startRecording = async () => {
		console.log('[DEBUG] startRecording function called.');
		// 1. Get microphone access
		try {
			hostAudioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
			console.log('[DEBUG] ✅ Microphone access granted.');
		} catch (err) {
			console.error('[DEBUG] ❌ Error getting host microphone:', err);
			alert('Could not access microphone. Please grant permission and try again.');
			return;
		}

		// 2. Find a supported audio format (FIX for 0KB file)
		const mimeTypes = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus'];
		const supportedMimeType = mimeTypes.find(type => MediaRecorder.isTypeSupported(type));

		if (!supportedMimeType) {
			alert('Sorry, your browser does not support the required audio formats for recording.');
			console.error('[DEBUG] ❌ No supported audio mimeType found.');
			hostAudioStream.getTracks().forEach(track => track.stop());
			return;
		}
		console.log(`[DEBUG] Using supported audio format: ${supportedMimeType}`);

		// 3. Create and configure MediaRecorder
		hostRecorder = new MediaRecorder(hostAudioStream, { mimeType: supportedMimeType });

		hostRecorder.ondataavailable = (event) => {
			console.log(`[DEBUG] Audio data available. Size: ${event.data.size}`);
			if (event.data.size > 0 && socket && socket.readyState === WebSocket.OPEN) {
				socket.send(event.data);
			}
		};

		hostRecorder.onstart = () => {
			console.log('[DEBUG] ✅ Host MediaRecorder started. Sending start_all command.');
			sendCommand('start_all');
			page = 2; // Update UI
		};

		hostRecorder.onstop = () => {
			console.log('[DEBUG] ✅ Host MediaRecorder stopped. Cleaning up audio tracks.');
			hostAudioStream?.getTracks().forEach(track => track.stop());
			hostAudioStream = null;
			hostRecorder = null;
		};

        hostRecorder.onerror = (event) => {
            console.error('[DEBUG] ❌ MediaRecorder error:', event.error);
        };

		// 4. Start the recorder
		console.log('[DEBUG] Calling recorder.start()');
		hostRecorder.start(1000); // Send data every 1 second
	};

	const stopRecording = () => {
		console.log('[DEBUG] stopRecording function called.');
		
		// 1. Tell server to stop all clients (FIX for stop command)
		sendCommand('stop_all');
		
		// 2. Stop the host's local recorder
		if (hostRecorder && hostRecorder.state === 'recording') {
			console.log('[DEBUG] Calling recorder.stop()');
			hostRecorder.stop();
		}
		
		// 3. Update UI
		page = 1;
	};

	onDestroy(() => {
		if (socket) {
			socket.close();
		}
		if (hostRecorder && hostRecorder.state === 'recording') {
			hostRecorder.stop();
		} else if (hostAudioStream) {
			hostAudioStream.getTracks().forEach(track => track.stop());
		}
	});
</script>

<main class:recording-active={page === 2}>
	<CompactDisc />

	{#if page === 0}
		<div class="page-container">
			<div class="placeholder"></div>
			<div class="placeholder__action">
				<button 
					class="btn--white" 
					onclick={initiateConnection}
					disabled={isConnecting}
				>
					{#if isConnecting}
						CONNECTING...
					{:else}
						CONNECT
					{/if}
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
						<img
							src="/tablet-android.svg"
							class:inactive={clients.length <= i}
							alt="Device {i + 1}"
						/>
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
	
	main.recording-active {
		background: #ff3434;
	}
	
	.page-container {
		height: 100%;
		display: flex;
		flex-direction: column;
	}
	
	.placeholder {
		flex: 1;
	}
	
	.placeholder:last-child {
		display: flex;
		align-items: flex-end;
	}
	
	.contents {
		margin-inline: 2rem;
	}

	.placeholder__action {
		margin-bottom: 2rem;
		width: 100%;
		padding-inline: 2rem;
	}

	.content h1,
	.contents h1 {
		text-align: center;
		font-size: 1rem;
		font-weight: 700;
		margin-bottom: 1rem;
	}

	.content__devices {
		display: flex;
		justify-content: center;
		align-items: center;
		margin-top: 1rem;
	}
	
	.content__devices img {
		margin-inline: 0.1rem;
		height: 1.5rem;
		filter: brightness(0) saturate(100%) invert(100%) sepia(6%) saturate(144%)
			hue-rotate(230deg) brightness(119%) contrast(100%);
	}
	
	.content__devices img.inactive {
		filter: brightness(0) saturate(100%) invert(100%) sepia(6%) saturate(144%)
			hue-rotate(230deg) brightness(119%) contrast(100%) opacity(0.4);
	}
</style>
<script>
	import { onMount, onDestroy } from 'svelte';

	const speed = 0.05;
	let rotation = 0;
	let frame; // This will be 'undefined' on the server

	onMount(() => {
		const animate = () => {
			rotation += speed;
			frame = requestAnimationFrame(animate);
		};
		animate();
	});

	// This now safely handles both server and client environments
	onDestroy(() => {
		// Only try to cancel the animation if 'frame' has been assigned a value (in the browser)
		if (frame) {
			cancelAnimationFrame(frame);
		}
	});
</script>

<main>
	<div class="img" style:transform="translateY(-50%) rotate({rotation}deg)">
		<img src="/mishran-high.png" alt="" />
	</div>
</main>

<style>
	.img {
		position: fixed;
		top: 0;
	}
	img {
		width: 100vw;
	}
</style>
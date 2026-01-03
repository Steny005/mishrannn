<script>
    import '../app.css'; 
    import favicon from '$lib/assets/favicon.svg';
    import { onNavigate } from '$app/navigation';

    // Destructure children from props (Svelte 5 syntax)
    let { children } = $props();

    // View Transition Logic
    onNavigate((navigation) => {
        if (!document.startViewTransition) return;

        return new Promise((resolve) => {
            document.startViewTransition(async () => {
                resolve();
                await navigation.complete;
            });
        });
    });
</script>

<svelte:head>
    <link rel="icon" href={favicon} />
</svelte:head>

{@render children?.()}
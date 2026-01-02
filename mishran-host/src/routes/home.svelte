<script>

</script>

<main>
    <div class="placeholder">

    </div>
    <div class="content">
        <h1>CONNECTED</h1>
        <div class="content__devices">
            <img src="/tablet-android.svg" class="inactive" alt="">
            <img src="/tablet-android.svg" class="inactive" alt="">
            <img src="/tablet-android.svg" class="inactive" alt="">
            <img src="/tablet-android.svg" class="inactive" alt="">
        </div>
    </div>
    <div class="placeholder">
        <div class="placeholder__action">
            <button class="btn--white">RECORD</button>
        </div>
    </div>
</main>

<style>
main {
    background: black;
    height: 100vh;
    color: white;
    display: flex;
    flex-direction: column;
}
.placeholder {
    flex: 1;
}
.content h1 {
    text-align: center;
    font-size: 1rem;
    font-weight: 700;
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
    filter: brightness(0) saturate(100%) invert(100%) sepia(6%) saturate(144%) hue-rotate(230deg) brightness(119%) contrast(100%);
}
.content__devices img.inactive {
    filter: brightness(0) saturate(100%) invert(100%) sepia(6%) saturate(144%) hue-rotate(230deg) brightness(119%) contrast(100%) opacity(0.4);
}
.placeholder:last-child {
    display: flex;
    align-items: flex-end;
}
.placeholder__action {
    margin: 1rem;
    width: 100%;
}
</style>
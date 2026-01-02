<script>

</script>

<main>
    <div class="placeholder">

    </div>
    <div class="content">
        <h1>RECORDING</h1>
    </div>
    <div class="placeholder">
        <div class="placeholder__action">
            <button class="btn--outline">STOP</button>
        </div>
    </div>
</main>

<style>
main {
    background: #ff3434;
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
.placeholder:last-child {
    display: flex;
    align-items: flex-end;
}
.placeholder__action {
    margin: 1rem;
    width: 100%;
}
</style>
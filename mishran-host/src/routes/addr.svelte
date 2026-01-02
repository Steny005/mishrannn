<script></script>

<main>
   <div class="placeholder">

   </div> 
   <div class="contents">
        <h1>IP ADDRESS</h1>
        <div class="matrix">
            <div class="matrix__row">
                <div class="matrix__column">
                    <p>1</p>
                </div>
                <div class="matrix__column">
                    <p>2</p>
                </div>
                <div class="matrix__column">
                    <p>3</p>
                </div>
            </div>
            <div class="matrix__row">
                <div class="matrix__column">
                    <p>4</p>
                </div>
                <div class="matrix__column">
                    <p>5</p>
                </div>
                <div class="matrix__column">
                    <p>6</p>
                </div>
            </div>
            <div class="matrix__row">
                <div class="matrix__column">
                    <p>7</p>
                </div>
                <div class="matrix__column">
                    <p>8</p>
                </div>
                <div class="matrix__column">
                    <p>9</p>
                </div>
            </div>
            <div class="matrix__row">
                <div class="matrix__column">
                    <p>.</p>
                </div>
                <div class="matrix__column">
                    <p>0</p>
                </div>
                <div class="matrix__column">
                    <p>C</p>
                </div>
            </div>
            <div class="matrix__row">
                <div class="matrix__column">
                    <p>N</p>
                </div>
            </div>
        </div>
   </div>
</main>

<style>
    main {
        background: black;
        height: 100vh;
        display: flex;
        color: white;
        flex-direction: column;
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
    }
    .matrix {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        margin: 0 1rem ;
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
    .matrix__row:last-child .matrix__column p{
        color: white;
    }
    .matrix__column {
        padding: 1rem;
    }
    .matrix__column p {
        font-weight: 700;
        color: #666;
        font-size: 1.25rem;
        transition: all ease 0.3s; 
    }
    .matrix__column p:hover {
        color: white;
    }
</style>
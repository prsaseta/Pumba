// Animación de empezar turno
function animateBeginTurn(gstate){
    // Comprobamos si es tu turno
    // Comprobamos que sea tu turno *y* no hayas sido tú quien haya terminado el turno
    if (gstate['current_player'] == playerIndex && gstate['action']['player'] != playerName){
        var ttext = scene.add.text(-500, 1080 / 2, "Your turn!", { fontFamily: 'Verdana', fontSize: 80, backgroundColor: "#00ff00", align: "center" })
        ttext.setOrigin(0.5, 0.5)
        ttext.setX(-500)
        ttext.setY(1080 / 2)
        ttext.setDepth(99999)
        var ttween = scene.tweens.add({
            targets: ttext,
            x: 1920 / 2,
            y: 1080 / 2,
            ease: "Linear",
            duration: 1000,
            repeat: 0,
            yoyo: false,
            completeDelay: 500,
            onComplete: function() {
                var ttween2 = scene.tweens.add({
                    targets: ttext,
                    x: 1920 + 500,
                    y: 1080 / 2,
                    ease: "Linear",
                    duration: 1000,
                    repeat: 0,
                    yoyo: false,
                    onComplete: function() {
                        ttext.destroy()
                    }
                })
            }
        })
        scene.sound.play("your-turn-sound")
    }

    // Repintamos la UI
    updateGameFromState(gstate)
    // Guardamos que hemos terminado
    game_state_processing = false
}
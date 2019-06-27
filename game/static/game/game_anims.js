// Animación de empezar turno

function tweenTextMiddleScreen(text, config) {
    var ttext = scene.add.text(-500, 1080 / 2, text, config)
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
}

function animateBeginTurn(gstate){
    // Comprobamos si es tu turno
    // Comprobamos que sea tu turno *y* no hayas sido tú quien haya terminado el turno
    if (gstate['current_player'] == playerIndex){
        tweenTextMiddleScreen("Your turn!", { fontFamily: 'Verdana', fontSize: 80, backgroundColor: "#00ff00", align: "center" })
        scene.sound.play("your-turn-sound")
    } else {
        // Si es una IA quien empieza su turno, se lo salta
        if (gstate['players'][gstate['current_player']][2]){
            // No hace nada
        } else {
            tweenTextMiddleScreen(gstate['players'][gstate['current_player']][0] + "'s turn", { fontFamily: 'Verdana', fontSize: 80, backgroundColor: "#ff0000", align: "center" })
            scene.sound.play("enemy-turn-sound")
        }
    }

    // Repintamos la UI
    updateGameFromState(gstate)
    // Guardamos que hemos terminado
    game_state_processing = false
}

function animatePlayCard(gstate) {
    // Creamos un sprite fuera de la pantalla en la misma X que la pila de juego
    var cardsp = scene.add.sprite(-254 / 2 + 1920 / 2, -500, gstate['action']['card']['suit'] + "-" + gstate['action']['card']['number'])
    // Si la hemos jugado nosotros, repintamos nuestra mano del tirón para que no se vea feo
    // También repintamos los botones de la UI
    if (gstate['current_player'] == playerIndex) {
        drawYourHand(gstate)
        drawUI()
    }
    // Ponemos un sonido
    scene.sound.play("play-card-sound")
    // Le ponemos un tween para moverla a encima de la pila
    var cardtween = scene.tweens.add({
        targets: cardsp,
        x: -254 / 2 + 1920 / 2,
        y: 1080 / 3,
        ease: "Linear",
        duration: 300,
        repeat: 0,
        yoyo: false,
        completeDelay: 300,
        onComplete: function() {
            // Repintamos la UI
            updateGameFromState(gstate)
            // Eliminamos el sprite (ya no nos hace falta)
            cardsp.destroy()
            // Guardamos que hemos terminado
            game_state_processing = false
        }
    })
}

function animateDrawCard(gstate) {
    // Ponemos un sonido y listo
    scene.sound.play("draw-card-sound")
    // Repintamos la UI
    updateGameFromState(gstate)
    // Guardamos que hemos terminado
    game_state_processing = false
}

function animateDrawCardForced(gstate) {
    // Ponemos un sonido y listo
    scene.sound.play("draw-card-sound")
    // Repintamos la UI
    updateGameFromState(gstate)
    // Guardamos que hemos terminado
    game_state_processing = false
}
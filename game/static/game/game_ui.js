// Pone el botón para empezar la partida
function drawBeginMatch() {
    if (beginMatch_group == undefined) {
        beginMatch_group = scene.add.group()
    }
    var begin_match = scene.add.text(1920 / 3, 1080 - 1080 / 3, "Begin match", { fontFamily: 'Verdana', fontSize: 80 })
    beginMatch_group.add(begin_match)
    begin_match.setInteractive()
    begin_match.setDepth(9999)

    function beginMatch() {
        gameSocket.send(JSON.stringify({
            'type': "begin_match"
        }));
    }

    begin_match.on("pointerup", beginMatch)
}

// Borra el botón de empezar partida y la notificación de quién la ha ganado
function deleteBeginMatch() {
    if (beginMatch_group != undefined) {
        beginMatch_group.clear(true, true)
    }
    if (wonMatch_group != undefined){
        wonMatch_group.clear(true, true)
    }
}

// Muestra el ganador en pantalla
function drawWinner(player) {
    if (wonMatch_group == undefined) {
        wonMatch_group = scene.add.group()
    } else {
        wonMatch_group.clear(true, true)
    }
    var winner = scene.add.text(1920 / 3, 150 + 1080 - 1080 / 3, player + " wins the match!", { fontFamily: 'Verdana', fontSize: 80 })
    wonMatch_group.add(winner)
    winner.setDepth(9999)
}

// Dibuja la UI básica
function drawUI() {
    if (ui_group == undefined) {
        ui_group = scene.add.group()
        var end_turn = scene.add.sprite(1920 - 200, 650, "end-turn")
        var draw_card = scene.add.sprite(1920 - 200, 500, "draw-card")

        end_turn.setInteractive()
        draw_card.setInteractive()

        ui_group.add(end_turn)
        ui_group.add(draw_card)

        function endTurn() {
            deleteSwitchButtons()
            gameSocket.send(JSON.stringify({
                'type': "begin_turn"
            }));
        }

        function drawCard() {
            gameSocket.send(JSON.stringify({
                'type': "draw_card"
            }));
        }

        end_turn.on("pointerup", endTurn)
        draw_card.on("pointerup", drawCard)
    }
}

// Pone en pantalla tu mano actual, borrando lo que hubiere
function drawYourHand() {
    // Buscamos el grupo, y si no está, lo borramos
    if (hand_group != undefined) {
        hand_group.clear(true, true)
    } else {
        hand_group = scene.add.group()
    }

    // Creamos los sprites
    // Centro alrededor del cual se ponen las cartas
    var center = (1920 / 2) + 254 / 2
    // Número de cartas que hay que distribuir
    var card_count = game_state["hand"].length
    // Ángulo alrededor del cual distribuir las cartas
    var angle = 45
    // Radio horizontal alrededor del cual distribuir las cartas (pixeles)
    var radius = 500 + (card_count - 1) * 100
    radius = Math.min(radius, 1920)
    for (i = 0; i < card_count; i++){
        // Carta actual
        var card = game_state["hand"][i]
        var disp = scene.add.sprite(((1920 - radius) / 2) + ((radius * i) / card_count), 1080 - 352/2 - 30, card[0] + "-" + card[1]).setInteractive();
        disp.setScale(Math.min(1.5 / Math.log(card_count), 1.25))
        disp.setDepth(i)
        //disp.setAngle((-angle) + (angle / card_count) * (i + 1))
        // TODO Probar esto: this.add.image(0, 0, 'sky').setOrigin(0, 0)
        // Le añadimos una propiedad no nativa al objeto, que es básicamente el índice de la carta en la mano
        // Se usa para ordenar la mano gráficamente y enviar comandos al servidor
        disp.custom_var = i
        hand_group.add(disp)

        // Los muertos de JavaScript y su retraso con las funciones me cago en dios
        // Hace que al hacer mouseover en la carta la ponga más grande
        var child = disp
        function changeScale2(child) {
            return function() {
                child.setScale(1.5)
                child.setDepth(10000)
                child.setY(child.y - 100)
            }
        }
        function changeScale1(child) {
            return function() {
                child.setScale(Math.min(1.5 / Math.log(card_count), 1.25))
                child.setDepth(child.custom_var)
                child.setY(child.y + 100)
            }
        }
        function playCardFromHand(child, suit, number) {
            return function() {
                gameSocket.send(JSON.stringify({
                    'type': "play_card",
                    'index': child.custom_var
                }));
            }
        }
        child.on('pointerover',changeScale2(child))
        child.on('pointerout',changeScale1(child))
        child.on('pointerup',playCardFromHand(child, card[0], card[1]))
    }
}

// Pone en pantalla los indicadores de otros jugadores
function drawPlayers(){
    // Borramos lo que hubiera, si lo hay
    if (players_group != undefined) {
        players_group.clear(true, false)
    } else {
        players_group = scene.add.group()
    }

    var num_players = game_state["players"].length
    var players_left = Math.ceil((num_players - 1) / 2)
    var players_right = Math.floor((num_players - 1) / 2)

    for(i = 0; i < num_players; i++){
        var text = game_state["players"][i][0] + " " + game_state["players"][i][1]
        if (game_state["players"][i][2] == "True") {
            text = "(AI) " + text
        }
        if (game_state["current_player"] == i) {
            text = text + " | CURRENT"
        }
        var ptext = scene.add.text(20, 20 + i * 70, text, { fontFamily: 'Verdana', fontSize: 36 });
        players_group.add(ptext)
        //scene.add.text(100, 100 + i * 100 + 50, game_state["players"][i][1], { fontFamily: 'Verdana', fontSize: 40 });
    }
}

// Pone en pantalla las pilas de juego
// TODO Poner las cartas una encima de otra visualmente para ponerlo bonito
function drawPiles() {
    // Borramos lo que hubiera, si lo hay
    if (piles_group != undefined) {
        piles_group.clear(true, true)
    } else {
        piles_group = scene.add.group()
    }

    var playPileDisp = scene.add.sprite(-254 / 2 + 1920 / 2, 1080 / 3, game_state["last_suit"] + "-" + game_state["last_number"])
    var playPileText = scene.add.text(-254 / 2 + 1920 / 2, 50 + 254 / 2 + 1080 / 3, game_state["play_pile"], { fontFamily: 'Verdana', fontSize: 36 });
    var drawPileDisp = scene.add.sprite(-254 / 2 + 300 + 1920 / 2, 1080 / 3, "card-back")
    var drawPileText = scene.add.text(-254 / 2 + 300 + 1920 / 2, 50 + 254 / 2 + 1080 / 3, game_state["draw_pile"], { fontFamily: 'Verdana', fontSize: 36 });
    piles_group.add(playPileDisp)
    piles_group.add(drawPileDisp)
    piles_group.add(drawPileText)
    piles_group.add(playPileText)
}

// Se ejecuta cuando recibes un divine
function drawDivine(suit, number) {
    if (divine_group == undefined) {
        divine_group = scene.add.group()
    } else {
        divine_group.clear(true, true)
    }

    var divination = scene.add.sprite(-30 -254 - 254 / 2 + 1920 / 2, 1080 / 3, suit + "-" + number)
    var divText = scene.add.text(-30 - 60 -254 - 254 / 2 + 1920 / 2, 20 + 352 / 2 + 1080 / 3, "Divination", { fontFamily: 'Verdana', fontSize: 36 })
    divine_group.add(divination)
    divine_group.add(divText)

    function clearDivination() {
        divine_group.clear(true, true)
    }

    divination.setInteractive()
    divination.on("pointerup", clearDivination)
}

 // Crea los botones de SWITCH
// Ojo: Hay que borrarlos después y poner que aparezcan solamente cuando haga falta
function drawSwitchButtons() {
    if (switchButtons_group != undefined) {
        //switchButtons_group.clear(true, true)
    } else {
        switchButtons_group = scene.add.group()
    }

    var espadas = scene.add.text(1920 - 200, 700, "ESPADAS", { fontFamily: 'Verdana', fontSize: 30 });
    var bastos = scene.add.text(1920 - 200, 700 + 50, "BASTOS", { fontFamily: 'Verdana', fontSize: 30 });
    var copas = scene.add.text(1920 - 200, 700 + 100, "COPAS", { fontFamily: 'Verdana', fontSize: 30 });
    var oros = scene.add.text(1920 - 200, 700 + 150, "OROS", { fontFamily: 'Verdana', fontSize: 30 });

    espadas.setInteractive()
    bastos.setInteractive()
    copas.setInteractive()
    oros.setInteractive()

    function switchEspadas() {
        gameSocket.send(JSON.stringify({
            'type': "switch_effect",
            'switch': "ESPADAS"
        }));
        deleteSwitchButtons()
    }
    
    function switchBastos() {
        gameSocket.send(JSON.stringify({
            'type': "switch_effect",
            'switch': "BASTOS"
        }));
        deleteSwitchButtons()
    }

    function switchCopas() {
        gameSocket.send(JSON.stringify({
            'type': "switch_effect",
            'switch': "COPAS"
        }));
        deleteSwitchButtons()
    }

    function switchOros() {
        gameSocket.send(JSON.stringify({
            'type': "switch_effect",
            'switch': "OROS"
        }));
        deleteSwitchButtons()
    }

    espadas.on('pointerup',switchEspadas)
    bastos.on('pointerup',switchBastos)
    copas.on('pointerup',switchCopas)
    oros.on('pointerup',switchOros)

    switchButtons_group.add(espadas)
    switchButtons_group.add(bastos)
    switchButtons_group.add(copas)
    switchButtons_group.add(oros)
    
}

function deleteSwitchButtons() {
    if (switchButtons_group != undefined) {
        switchButtons_group.clear(true, true)
    }
}

function drawTurnDirection() {
    if (turnDirection_group != undefined) {
        turnDirection_group.clear(true, true)
    } else {
        turnDirection_group = scene.add.group()
    }

    var turnDirText = scene.add.text(1920 / 2, 20, game_state["turn_direction"], { fontFamily: 'Verdana', fontSize: 30 });
    turnDirection_group.add(turnDirText)
}

// Muestra en pantalla el contador de robo (si hay)
function drawDrawCounter() {
    // Borramos lo que hubiera, si lo hay
    if (drawCounter_group != undefined) {
        drawCounter_group.clear(true, true)
    } else {
        drawCounter_group = scene.add.group()
    }

    if (game_state["draw_counter"] > 0) {
        var drawCounterText = scene.add.text(1600, 20, "Counter: " + game_state["draw_counter"], { fontFamily: 'Verdana', fontSize: 30 });
        drawCounter_group.add(drawCounterText)
    }
}
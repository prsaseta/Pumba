// Pone el botón para empezar la partida
function drawBeginMatch() {
    if (beginMatch_group == undefined) {
        beginMatch_group = scene.add.group()
    }
    var begin_match = scene.add.text(1920 / 3, 1080 - 1080 / 3, "Begin match", { fontFamily: 'Verdana', fontSize: 80, backgroundColor: "#0000ff", align: "center" })
    beginMatch_group.add(begin_match)
    begin_match.setInteractive()
    begin_match.setOrigin(0.5, 0.5)
    begin_match.setX(1920 / 2)
    begin_match.setY(100 + 1080 / 2)
    begin_match.setDepth(9999)

    function beginMatch() {
        gameSocket.send(JSON.stringify({
            'type': "begin_match"
        }));
        // Esto último no sirve para nada si todo va bien, pero a veces en local se pierde un mensaje y viene bien actualizar
        gameSocket.send(JSON.stringify({
            'type': "game_state"
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
    var winner = scene.add.text(1920 / 3, 150 + 1080 - 1080 / 3, player + " wins the match!", { fontFamily: 'Verdana', fontSize: 80, backgroundColor: "#00ff00", align: "center" })
    wonMatch_group.add(winner)
    winner.setDepth(9999)
    winner.setOrigin(0.5, 0.5)
    winner.setX(1920 / 2)
    winner.setY(1080 / 2)
}

// Dibuja la UI básica
function drawUI() {
    if (ui_group == undefined) {
        ui_group = scene.add.group()
    } else {
        ui_group.clear(true, true)
    }

    var end_turn = scene.add.sprite(1920 - 150, 500, "end-turn")
    var draw_card = scene.add.sprite(1920 - 350, 500, "draw-card")

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

    // Tintamos los botones si no se pueden usar
    // Le ponemos que en hover se vean más grandes también
    if (!can_end_turn) {
        end_turn.setTint(0xaaaaaa)
    } else {
        end_turn.setTint(0xffffff)
        end_turn.on("pointerover", function() {
            end_turn.setScale(1.5)
        })
        end_turn.on("pointerout", function() {
            end_turn.setScale(1)
        })
    }

    if (drawn_this_turn > 1){
        draw_card.setTint(0xaaaaaa)
    } else {
        draw_card.setTint(0xffffff)
        draw_card.on("pointerover", function() {
            draw_card.setScale(1.5)
        })
        draw_card.on("pointerout", function() {
            draw_card.setScale(1)
        })
    }
}

// Pone en pantalla tu mano actual, borrando lo que hubiere
// Permite pasarle un game state custom; si no, coge el estado actual
function drawYourHand(gamestate = undefined) {
    // Buscamos el grupo, y si no está, lo borramos
    if (hand_group != undefined) {
        hand_group.clear(true, true)
    } else {
        hand_group = scene.add.group()
    }

    if (gamestate == undefined) {
        gamestate = game_state
    }

    // Creamos los sprites
    // Centro alrededor del cual se ponen las cartas
    var center = (1920 / 2) + 254 / 2
    // Número de cartas que hay que distribuir
    var card_count = gamestate["hand"].length
    // Ángulo alrededor del cual distribuir las cartas
    var angle = 45
    // Radio horizontal alrededor del cual distribuir las cartas (pixeles)
    var radius = 500 + (card_count - 1) * 100
    radius = Math.min(radius, 1920)
    for (i = 0; i < card_count; i++){
        // Carta actual
        var card = gamestate["hand"][i]
        // Marcamos si la carta es jugable o no para destacarla visualmente
        var can_be_played = undefined

        // Comprobamos si hay contador de robo (y que no lo has reflejado): si lo hay, solamente marcamos ONE, TWO y COPY
        if (gamestate['draw_counter'] != 0 && !has_played_card){
            if (card[1] == "ONE" || card[1] == "TWO" || (card[1] == "COPY" && card[0] == gamestate["last_suit"])) {
                can_be_played = true
            } else {
                can_be_played = false
            }
        // Si ha jugado un rey este turno, solamente marcamos las cartas que se puedan jugar
        } else if (has_played_king) {
            if (card[0] == gamestate["last_suit"]) {
                can_be_played = true
            } else {
                can_be_played = false
            }
        // Si ha jugado una carta que no es rey, no puede jugar más
        } else if (has_played_card) {
            can_be_played = false
        // Si no hay contador de robo y no está jugando un rey y no ha jugado carta, la marcamos si comparte número o palo con la última
        } else {
            if (card[1] == gamestate['last_number'] || card[0] == gamestate['last_suit']) {
                can_be_played = true
            } else {
                can_be_played = false
            }
        }

        var disp = scene.add.sprite(((1920 - radius) / 2) + ((radius * i) / card_count), 1080 - 352/2 - 30, card[0] + "-" + card[1]).setInteractive();
        disp.setScale(Math.min(1.5 / Math.log(card_count), 1.25))
        disp.setDepth(i)
        // Le añadimos una propiedad no nativa al objeto, que es básicamente el índice de la carta en la mano
        // Se usa para ordenar la mano gráficamente y enviar comandos al servidor
        disp.custom_var = i
        hand_group.add(disp)

        // Marcamos la carta dependiendo de su jugabilidad
        if (can_be_played) {
            // No hace nada
        } else {
            // La pone un poco gris
            disp.setTint(0xaaaaaa)
        }

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

function drawPlayers() {
    // Borramos lo que hubiera, si lo hay
    if (players_group != undefined) {
        players_group.clear(true, false)
    } else {
        players_group = scene.add.group()
    }

    // Dividimos la parte de arriba en la pantalla entre el número de jugadores
    var num_players = Math.max(game_state["players"].length, 1)
    var width_assigned = (1920 - 100) / num_players

    // Por cada jugador
    for(i = 0; i < num_players; i++){
        // Cogemos su username y le añadimos "(IA)" si es una IA
        var text = game_state["players"][i][0]
        if (game_state["players"][i][2] == "True") {
            text = text + "(AI) "
        }
        // Calculamos dónde debería ir
        var xpos = i * width_assigned + (1/2) * width_assigned
        // Creamos el texto
        var ptext = scene.add.text(xpos, 10, text, { fontFamily: 'Verdana', fontSize: 24, align: 'center', wordWrap: { width: width_assigned, useAdvancedWrap: true } });
        // Al jugador actual lo pintamos con otro color
        if (game_state["current_player"] == i) {
            ptext.setColor("#00ff00")
        }
        // Añadimos el objeto texto al grupo
        players_group.add(ptext)
        var last_j = 0
        // Pintamos las cartas que tiene en la mano
        var z = 0
        var maxi = game_state["players"][i][1]
        for (j = 0; j < maxi; j++){
            // Posición y
            var ypos = 80
            // Si el jugador tiene un nombre largo y ocupa dos líneas, movemos las cartas un poco para abajo
            if (ptext.getWrappedText(text).length > 1){
                ypos = ypos + 20
            }
            // Añadimos el sprite de la carta
            var unknown_card = undefined
            // Si sabemos qué carta es por DIVINE (y no es de las nuestras), la pintamos
            var pvined = getPlayersDivined()
            if (i == playerIndex) {
                unknown_card = scene.add.sprite(xpos + j * 20, ypos, "card-back")
            } else if (pvined[i] != undefined && j >  maxi - pvined[i].length - 1) {
                var dcard = pvined[i][z]
                z += 1
                unknown_card = scene.add.sprite(xpos + j * 20, ypos, dcard['suit'] + "-" + dcard['number'])
            // Si no, pintamos un cardback genérico
            } else {
                unknown_card = scene.add.sprite(xpos + j * 20, ypos, "card-back")
            }
            
            // La hacemos más pequeña
            unknown_card.setScale(0.15, 0.15)
            // La añadimos al grupo
            players_group.add(unknown_card)
            // Actualizamos el último j (es para dibujar justo después del loop un número)
            last_j = j
            // Si ya hay muchas cartas, no dibujamos más
            if (j > 10) {
                break
            }
        }
        // Pintamos aparte el número de cartas que tenga en mano
        var cardn = scene.add.text(xpos + (last_j + 1) * 20, ypos, maxi, { fontFamily: 'Verdana', fontSize: 24, align: 'right'});
        players_group.add(cardn)
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

    var espadas = scene.add.sprite(1920 - 500 +50, 350, "button-espadas");
    var bastos = scene.add.sprite(1920 - 375 +50, 350, "button-bastos");
    var copas = scene.add.sprite(1920 - 250 +50, 350, "button-copas");
    var oros = scene.add.sprite(1920 - 125 +50, 350, "button-oros");

    espadas.setScale(0.5, 0.5)
    bastos.setScale(0.5, 0.5)
    copas.setScale(0.5, 0.5)
    oros.setScale(0.5, 0.5)

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
    var text = undefined
    if (game_state["turn_direction"] == "CLOCKWISE"){
        text = ">>>"
    } else {
        text = "<<<"
    }
    var turnDirText = scene.add.text(1920 / 2, 130, text, { fontFamily: 'Verdana', fontSize: 26, align: "center" });
    turnDirText.setOrigin(0.5, 0)
    turnDirText.setX(1920 / 2)
    turnDirText.setY(120)
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
        var drawCounterText = scene.add.text(25 + 1920 / 2, 580, game_state["draw_counter"], { fontFamily: 'Verdana', fontSize: 66 });
        var drawCounterImg = scene.add.sprite(-10 + 1920 / 2, 620, "forced-draw")
        drawCounterImg.setScale(0.4, 0.4)
        drawCounter_group.add(drawCounterText)
        drawCounter_group.add(drawCounterImg)
    }
}
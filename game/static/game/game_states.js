function processEndTurn(gstate) {
    // Actualizamos el estado de los botones de la UI y variables varias
    // Si el jugador actual ha empezado su turno:
    if (gstate['current_player'] == playerIndex) {
        drawn_this_turn = 0
        can_end_turn = false
    // Si acaba de terminarlo:
    } else {
        drawn_this_turn = 2
        can_end_turn = false
    }
    has_played_king = false
    has_played_card = false
    
    // Actualizamos el historial
    var cbox_message = "Player " + gstate['action']['player'] + " ends their turn."
    appendToRecord(cbox_message)

    // Animación de fin de turno
    animateBeginTurn(gstate)
}

function processBeginMatch(gstate) {
    // Si el jugador actual empieza, resalta en la interfaz lo que puede hacer
    if (gstate['current_player'] == playerIndex) {
        drawn_this_turn = 0
        can_end_turn = false
    // Si el jugador actual no puede hacer nada, lo pone todo gris
    } else {
        drawn_this_turn = 2
        can_end_turn = false
    }

    // Borramos el botón para empezar la partida
    deleteBeginMatch()
    // Añadimos lo que ha pasado al historial
    var cbox_message = "The match has begun!"
    appendToRecord(cbox_message)

    // Repintamos la UI
    updateGameFromState(gstate)
    
    // Guardamos que hemos terminado
    game_state_processing = false
}

function processDrawCard(gstate) {
    // Actualizamos el estado de los botones de la UI
    // Si el jugador actual ha robado carta:
    if (gstate['current_player'] == playerIndex) {
        drawn_this_turn += 1
        if (drawn_this_turn > 1) {
            can_end_turn = true
        }
    }
    // Si sabíamos qué carta era, nos la apuntamos
    if (last_divined != undefined){
        var pvined = getPlayersDivined()
        pvined[gstate['current_player']].push(last_divined)
        last_divined = undefined
        divine_group.clear(true, true)
    }

    // Añadimos lo que ha pasado al historial
    var cbox_message = "Player " + gstate['action']['player'] + " draws a card."
    appendToRecord(cbox_message)

    animateDrawCard(gstate)
}

function processDrawCardForced(gstate) {
    // Actualizamos el estado de los botones de la UI
    // Si el jugador actual ha robado carta forzadamente:
    if (gstate['current_player'] == playerIndex) {
        drawn_this_turn = 2
        can_end_turn = true
    }
    // Si sabíamos qué carta era, nos la apuntamos
    if (last_divined != undefined){
        var pvined = getPlayersDivined()
        pvined[gstate['current_player']].push(last_divined)
        last_divined = undefined
        divine_group.clear(true, true)
    }

    // Añadimos lo que ha pasado al historial
    var cbox_message = "Player " + gstate['action']['player'] + " draws " + gstate['action']['number'] + " cards and resets the counter."
    appendToRecord(cbox_message)

    animateDrawCardForced(gstate)
}

// Se ejecuta cuando la partida termina
// Dibuja el ganador en pantalla y el botón para reiniciar la partida (si eres el host)
function gameWon(player) {
    if (game_state["host"] == playerIndex) {
        drawBeginMatch()
    }
    drawWinner(player)
    scene.sound.play("game-won-sound")
    // Reseteamos también la cola de estados para liberar memoria
    game_state_queue = [undefined]
    game_state_index = 0

    has_played_card = false
    has_played_king = false
    can_end_turn = false
    drawn_this_turn = 0
}

function processGameWon(gstate) {
    // Repintamos la UI
    updateGameFromState(gstate)

    // Ponemos al ganador
    gameWon(gstate['action']['player'])

    // Vaciamos el tema de DIVINE para la siguiente partida
    players_divined = undefined
    last_divined = undefined
    clearDivination()

    // Eliminamos los botones de SWITCH, por si hemos terminado jugando uno
    deleteSwitchButtons()

    // Añadimos lo que ha pasado al registro
    var cbox_message = gstate['action']['player'] + " wins the match!"
    appendToRecord(cbox_message)

    // Guardamos que hemos terminado
    game_state_processing = false
}

function processPlayCard(gstate) {
    // Actualizamos el estado de los botones de la UI
    // Si el jugador actual ha jugado carta:
    if (gstate['current_player'] == playerIndex) {
        can_end_turn = true
        drawn_this_turn = 2
        // Si la carta es un SWITCH, además dibujamos los botones de SWITCH
        if (gstate['last_effect'] == 'SWITCH') {
            drawSwitchButtons()
        // Si ha jugado un rey, actualizamos la variable (para dibujar mejor cartas y cosas de la UI)
        } else if (gstate['last_effect'] == "KING") {
            has_played_king = true
        }
        has_played_card = true
    }
    // Eliminamos la carta que sabíamos que tenía si la juega
    var pvined = getPlayersDivined()
    for (i = 0; i < pvined[gstate['current_player']].length; i++){
        var ccard = pvined[gstate['current_player']][i]
        if (gstate['action']['card']['suit'] == ccard['suit'] && gstate['action']['card']['number'] == ccard['number']) {
            pvined[gstate['current_player']].splice(i, 1)
            break
        }
    }

    // Añadimos lo que ha pasado al historial
    var cbox_message = "Player " + gstate['action']['player'] + " plays a " + gstate['action']['card']['number'] + " of " + gstate['action']['card']['suit'] + "."
    appendToRecord(cbox_message)

    animatePlayCard(gstate)
}

function processSwitch(gstate) {
    // Añadimos lo que ha pasado al historial
    var cbox_message = "Player " + gstate['action']['player'] + " changes the current suit to " + gstate['action']['suit'] + "."
    appendToRecord(cbox_message)

    // Actualizamos la UI
    updateGameFromState(gstate)

    // Guardamos que hemos terminado
    game_state_processing = false
}

// Pinta TODO de nuevo
function updateDisplay() {
    drawUI()
    drawYourHand()
    drawPlayers()
    drawPiles()
    drawDrawCounter()
    drawTurnDirection()
}

// Actualiza el estado de juego, pintando en pantalla lo que haga falta
// data: Paquete de datos recibido del servidor. Tiene un estado y una acción que ha llevado a dicho estado.
function updateGameFromState(data) {
    // El primer estado es "undefined"
    if (data == undefined){
        return undefined;
    }
    game_state["game_status"] = data["game_status"]
    game_state["last_suit"] = data["last_suit"]
    game_state["last_number"] = data["last_number"]
    game_state["last_effect"] = data["last_effect"]
    game_state["current_player"] = data["current_player"]
    game_state["next_player"] = data["next_player"]
    game_state["turn_direction"] = data["turn_direction"]
    game_state["draw_counter"] = data["draw_counter"]
    game_state["draw_pile"] = data["draw_pile"]
    game_state["play_pile"] = data["play_pile"]
    game_state["hand"] = data["hand"]
    game_state["players"] = data["players"]
    game_state["host"] = data["host"]

    // Recuperamos nuestro nombre
    if (playerName == undefined) {
        playerName = data["players"][playerIndex][0]
    }

    // Si se está esperando a empezar, muestra el botón para empezar la partida
    if (game_state["game_status"] != "PLAYING" && data["host"] == playerIndex) {
        drawBeginMatch()
    }
    // Si no se está esperando, actualiza el HUD
    if (game_state["game_status"] != "WAITING") {
        updateDisplay()
    }
}

// Se llama a esta función cuando haya un estado pendiente de mostrar en la pantalla
// Inicia la animación correspondiente al siguiente estado y actualiza el pointer
function startPlayingStates(){
    // Marcamos que ya estamos procesando los estados, para no pisarnos
    game_state_processing = true
    // Nos aseguramos de que haya algo que hacer
    if (game_state_index < game_state_queue.length -1) {  
        // Recogemos el estado siguiente
        game_state_index += 1
        var gstate = game_state_queue[game_state_index]

        // Hacemos animaciones y eso
        if (gstate != undefined) {
            // Si no ha pasado nada, repintamos directamente
            if (gstate['action'] == undefined) {
                // Repintamos la UI
                updateGameFromState(gstate)
                // Guardamos que hemos terminado
                game_state_processing = false
            // Ponemos la animación correspondiente a lo que ha pasado
            } else {
                if (gstate['action']['type'] == "end_turn"){
                    processEndTurn(gstate)
                } else if (gstate['action']['type'] == "begin_match") {
                    processBeginMatch(gstate)
                } else if (gstate['action']['type'] == "game_won") {
                    processGameWon(gstate)
                } else if (gstate['action']['type'] == "play_card") {
                    processPlayCard(gstate)
                } else if (gstate['action']['type'] == "draw_card"){
                    processDrawCard(gstate)
                } else if (gstate['action']['type'] == "draw_card_forced"){
                    processDrawCardForced(gstate)
                } else if (gstate['action']['type'] == "switch") {
                    processSwitch(gstate)
                // Si ha llegado una acción desconocida, repintamos y listo
                // Esto no debería pasar nunca, es un failsafe
                } else {
                    // Repintamos la UI
                    updateGameFromState(gstate)
                    // Guardamos que hemos terminado
                    game_state_processing = false
                }
            }
        }
    } else {
        // Si no había nada que hacer...
        // Esto no debería ejecutarse, pero no hace daño dejarlo
        game_state_processing = false
    }
}
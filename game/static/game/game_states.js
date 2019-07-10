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

function processGameWon(gstate) {
    // Repintamos la UI
    updateGameFromState(gstate)

    // Ponemos al ganador
    gameWon(gstate['action']['player'])

    // Vaciamos esto para la siguiente partida
    players_divined = undefined

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

    // Guardamos que hemos terminado
    game_state_processing = false
}
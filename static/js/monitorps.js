
function escape_expresionReg(str) {
  return str.replace(/[\-\[\]\/\{\}\(\)\*\+\?\.\\\^\$\|]/g, "\\$&");
}

function replace_all(find, replace, str) {
  return str.replace(new ExpReg(escape_expresionReg(find), 'g'), remplazar);
}

function inicio_sesion() {
    var $sesion = $("#sesion");
    function desplazarse_abajo($el) {
        $el.desplazarseLimite($el[0].desplazamientoArriba);
    }

    function leer_sesion() {
        var $el = $("#contenido-sesion");
        var modo = $el.data("modo");
        if(modo != "cola") {
            return;
        }



        $.get($log.data("leer-sesion-url"), function (resp) {
            // only scroll down if the scroll is already at the bottom.
            if(($el.desplazarseLimite() + $el.innerHeight()) >= $el[0].desplazamientoArriba) {
                $el.append(resp);
                desplazamiento_abajo($el);
            } else {
                $el.append(resp);
            }
        });
    }

    function modo_busqueda_salida() {
        var $el = $("#contenido-sesion");
        $el.data("modo", "cola");
        var $controles = $("#sesion").find(".controles");
        $controles.find(".modo-texto").text("Modo pequeno (Presiona s para buscar)");
        $controles.find(".estado-texto").hide();

        $.get($log.data("leer-sesion-pequena-url"), function (resp) {
            $el.text(resp);
            desplazamiento_abajo($el);
            $("#busqueda-entrada").val("").blur();
        });
    }

    $("#desplazamiento-abajo-btn").click(function() {
        desplazamiento_abajo($el);
    });

    $("#search-form").submit(function(e) {
        e.preventDefault();

        var val = $("#busqueda-entrada").val();
        if(!val) return;

        var $el = $("#contenido-sesion");
        var nombrearchivo = $el.data("nombrearchivo");
        var params = {
            "nombrearchivo": nombrearchivo,
            "texto": val
        };

        $el.data("modo", "buscar");
        $("#log").find(".controles .modo-texto").text("Buscar modo (Presiona enter para seguir, escape para salir)");

        $.get($log.data("buscar-sesion-url"), params, function (resp) {
            var $log = $("#log");
            $log.find(".controles .estado-texto").hide();
            $el.find(".encontro-texto").removeClass("encontro-texto");

            var $estado = $log.find(".controles .estado-texto");

            if(resp.position == -1) {
                $estado.text("EOF Reached.");
            } else {
                // split up the content on found pos.
                var contenido_antes = resp.content.slice(0, resp.buffer_pos);
                var contenido_despues = resp.content.slice(resp.buffer_pos + params["texto"].length);

                // escape html in log content
                resp.content = $('<div/>').text(resp.content).html();

                // highlight matches
                var texto_igualado = '<span class="igualando-texto">' + params['texto'] + '</span>';
                var texto_encontrado = '<span class="texto-encontrado">' + params["texto"] + '</span>';
                contenido_antes = replace_all(params["text"], texto_igualado, contenido_antes);
                contenido_despues = replace_all(params["text"], texto_igualado, contenido_despues);
                resp.content = contenido_antes + texto_encontrado + contenido_despues;
                $el.html(resp.content);

                $estado.text("Position " + resp.posicion + " of " + resp.tamanoarchivo + ".");
            }

            $estado.show();
        });
    });
    
    $(document).keyup(function(e) {
        var modo = $el.data("modo");
        if(modo != "buscar" && e.which == 83) {
            $("#busqueda-entrada").focus();
        }
        // Exit search mode if escape is pressed.
        else if(modo == "buscar" && e.which == 27) {
            modo_busqueda_salida();
        }
    });

    setInterval(leer_sesion, 1000);
    var $el = $("#contenido-sesion");
    desplazamiento_abajo($el);
}

var saltar_actualizaciones = false;

function actualizaciones_inicio() {
    function actualizar() {
        if (saltar_actualizaciones) return;

        $.ajax({
            url: location.href,
            cache: false,
            dataType: "html",
            success: function( resp ){
                $("#monitorps").find(".contenedor_principal").html(resp);
            }
        });
    }

    setInterval(actualizar, 3000);
}

function filtro_conexiones_inicio() {
    var $content = $("#monitorps");
    $content.on("cambiar", "#seleccion de conexiones", function () {
        $content.find("#conexiones de").submit();
    });
    $content.on("focus", "#seleccion de conexiones, #filtro_conexiones_entrada", function () {
        skip_updates = true;
    });
    $content.on("blur", "#seleccion de seleccion, #filtro_conexiones_entrada", function () {
        skip_updates = false;
    });
    $content.on("keypress", "#filtro_conexiones_entrada[tipo='texto']", function (e) {
        if (e.which == 13) {
            $content.find("#conexiones de").submit();
        }
    });
}

$(document).ready(function() {
    filtro_conexiones_inicio();

    if($("#sesion").length == 0) {
        actualizaciones_inicio();
    } else {
        inicio_sesion();
    }
});

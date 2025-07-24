module ControllerModule

using Statistics

export get_action

function get_action(args;verbose=false)
    verbose && println("Got arguments: $args")
    return [2.0, -0.03]
end

end
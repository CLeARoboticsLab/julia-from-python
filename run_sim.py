import jax
from jax import numpy as jnp
import numpy as np
import mediapy
from tqdm import tqdm
import dataclasses
import pickle
import os
import sys
import random

from juliacall import Main as jl
jl.seval("using Pkg")
jl.seval(f'Pkg.activate("./")')

from waymax import config as _config, datatypes, dynamics, agents, visualization, env as _env

def run_sim(scenario_path: str="./data/scenario_iter_1.pkl", use_script: bool=True, verbose: bool=True):
    
    if use_script:
        jl.seval('include("./controller_script.jl")')
    else:
        jl.seval('include("./controller_module.jl")')
        jl.seval("using .ControllerModule")
    
    with open(scenario_path, 'rb') as f:
        scenario = pickle.load(f)

    dynamics_model = dynamics.InvertibleBicycleModel()
    env = _env.MultiAgentEnvironment(
        dynamics_model=dynamics_model,
        config=dataclasses.replace(
            _config.EnvironmentConfig(),
            max_num_objects=scenario.object_metadata.num_objects,
            controlled_object=_config.ObjectType.VALID,
        ),
    )

    agent_ids_to_log = [4, 3, 8, 2]
    id_to_idx_map = {i:int(id) for i, id in enumerate(scenario.object_metadata.ids)}
    
    template_state = env.reset(scenario)
    state_vectors = { "data": [] } # Create a mutable dictionary  entry to store the state vectors
    for obs_t in range(0,1):
        state_vectors["data"].append([])
        for x, y, yaw, vel_x, vel_y in zip(
                scenario.log_trajectory.x[agent_ids_to_log, obs_t],
                scenario.log_trajectory.y[agent_ids_to_log, obs_t],
                scenario.log_trajectory.yaw[agent_ids_to_log, obs_t],
                scenario.log_trajectory.vel_x[agent_ids_to_log, obs_t],
                scenario.log_trajectory.vel_y[agent_ids_to_log, obs_t]
            ):
            state_vectors["data"][-1].extend([float(x), float(y), float(jnp.sqrt(vel_x**2 + vel_y**2)), float(yaw)])

    state = dataclasses.replace(
        template_state,
        timestep=jnp.asarray(1),
    )
    states = [state]
    all_actions = []

    obj_idx = jnp.arange(scenario.object_metadata.num_objects)
    expert_actor = agents.create_expert_actor(
        is_controlled_func=lambda state: obj_idx != 4,
        dynamics_model=dynamics_model
    )

    def get_action(agent_states):
        if use_script:
            action = jl.seval(f"get_action({agent_states};verbose={str(verbose).lower()})")
        else:
            action = jl.seval(f"ControllerModule.get_action({agent_states};verbose={str(verbose).lower()})")
        dummy_action = jnp.array([0.0 for _ in range(len(action))])
        return [action if i == 4 else dummy_action for i in range(16)]
    
    controlled_actor = agents.actor_core_factory(
        lambda random_state: [0.0],
        lambda env_state, prev_agent_state, arg3, arg4: agents.WaymaxActorOutput(
            actor_state=jnp.array([0.0]),
            action=datatypes.Action(
                data=jnp.array(get_action(state_vectors["data"][-1])),
                valid=jnp.zeros((scenario.object_metadata.num_objects, 1), dtype=jnp.bool_).at[4, 0].set(True),
            ),
            is_controlled=jnp.zeros(scenario.object_metadata.num_objects, dtype=jnp.bool_).at[4].set(True),
        ),
    )
    agents.actor_core.register_actor_core(controlled_actor)
    actors = [expert_actor, controlled_actor]

    for t in range(states[0].remaining_timesteps):
        verbose and print(f"[run_sim] time: {t}")
        outputs = [actor.select_action({}, state, None, None) for actor in actors]
        action = agents.merge_actions(outputs)
        state = env.step(state, action)
        states.append(state)
        all_actions.append(action.data)
        state_vectors["data"].append([])
        for x, y, yaw, vel_x, vel_y in zip(
            state.current_sim_trajectory.x[agent_ids_to_log, -1:],
            state.current_sim_trajectory.y[agent_ids_to_log, -1:],
            state.current_sim_trajectory.yaw[agent_ids_to_log, -1:],
            state.current_sim_trajectory.vel_x[agent_ids_to_log, -1:],
            state.current_sim_trajectory.vel_y[agent_ids_to_log, -1:]
        ):
            if len(state_vectors["data"][-1]) > 0:
                state_vectors["data"][-1].pop()
            state_vectors["data"][-1].append([
                float(x[0]), 
                float(y[0]), 
                float(jnp.sqrt(vel_x**2 + vel_y**2)[0]), 
                float(yaw[0])
            ])

    verbose and print("[run_sim] Done!")
    verbose and print("[run_sim] videoing!")
    imgs = []
    for state in states:
        state_to_plot = state
        img = visualization.plot_simulator_state(state_to_plot, use_log_traj=False)
        imgs.append(img)
        
    mediapy.write_video(f"./data/sim.mp4", imgs, fps=10)
    verbose and print(f"[run_sim] video saved to ./data/sim.mp4")
    verbose and print("Done")

if __name__ == "__main__":
    verbose = False
    use_script = True
    for arg in sys.argv[1:]:
        if arg == "-v" or arg == "--verbose":
            verbose = True
        elif arg == "-m" or arg == "--module":
            use_script = False
        elif arg == "-s" or arg == "--script":
            use_script = True
    run_sim(verbose=verbose, use_script=use_script)
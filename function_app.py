import azure.functions as func
import logging
import random
import json
import requests

app = func.FunctionApp()

# Generate random task execution times (1 to 10 units)
def generate_task_times(num_tasks):
    return [random.randint(1, 10) for _ in range(num_tasks)]

# Generate an individual chromosome (task-to-core mapping)
def generate_individual(num_tasks, num_cores):
    """Generate a 1D array where position = task and value = assigned core."""
    return [random.randint(0, num_cores - 1) for _ in range(num_tasks)]

# Mutation function
def mutate(individual, mutation_rate, max_value=None):
    if random.random() < mutation_rate:
        task_to_mutate = random.randint(0, len(individual) - 1)
        new_core = random.randint(0, max_value)  # max_value is None by default
        individual[task_to_mutate] = new_core
    return individual

# Migration function
def migrate(islands, migration_rate):
    num_islands = len(islands)
    if num_islands < 2:
        return islands  # No migration if there's only one island
    for island_id in islands:
        if random.random() < migration_rate:
            target_island = random.choice([i for i in islands if i != island_id])
            migrant_index = random.randint(0, len(islands[island_id]) - 1)
            migrant = islands[island_id][migrant_index]
            islands[island_id][migrant_index] = random.choice(islands[target_island])
            islands[target_island].append(migrant)
    return islands

# Send to fitness function
FITNESS_TRIGGER_URL = "http://localhost:7071/api/fitnessTrigger"  # Local URL for fitnessTrigger

def send_to_fitness(data):
    try:
        response = requests.post(FITNESS_TRIGGER_URL, json=data)
        response.raise_for_status()  # Raise an exception for HTTP errors
        logging.info(f"Fitness response: {response.json()}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send data to fitnessTrigger: {e}")
        return None

# Validate parameters function
def validate_parameters(params):
    num_tasks = params.get('num_tasks')
    num_cores = params.get('num_cores')
    num_islands = params.get('num_islands')
    num_generations = params.get('num_generations')
    migration_interval = params.get('migration_interval')
    migration_rate = params.get('migration_rate')
    mutation_rate = params.get('mutation_rate')

    if not all([num_tasks, num_cores, num_islands, num_generations, migration_interval, migration_rate, mutation_rate]):
        return None, "Missing required parameters. Please ensure all parameters are provided."

    try:
        num_tasks = int(num_tasks)
        num_cores = int(num_cores)
        num_islands = int(num_islands)
        num_generations = int(num_generations)
        migration_interval = int(migration_interval)
        migration_rate = float(migration_rate)
        mutation_rate = float(mutation_rate)
    except ValueError as ve:
        return None, f"Invalid parameter value: {ve}"

    if num_tasks <= 0:
        return None, "Number of tasks must be greater than zero."
    if num_cores <= 0:
        return None, "Number of cores must be greater than zero."
    if num_islands <= 0:
        return None, "Number of islands must be greater than zero."
    if num_generations <= 0:
        return None, "Number of generations must be greater than zero."
    if migration_interval <= 0:
        return None, "Migration interval must be greater than zero."
    if not (0 <= migration_rate <= 1):
        return None, "Migration rate must be between 0 and 1."
    if not (0 <= mutation_rate <= 1):
        return None, "Mutation rate must be between 0 and 1."

    return {
        "num_tasks": num_tasks,
        "num_cores": num_cores,
        "num_islands": num_islands,
        "num_generations": num_generations,
        "migration_interval": migration_interval,
        "migration_rate": migration_rate,
        "mutation_rate": mutation_rate
    }, None

@app.route(route="population", auth_level="anonymous")
def init_population(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    validated_params, error_message = validate_parameters(req.params)
    if error_message:
        return func.HttpResponse(error_message, status_code=400)

    num_tasks = validated_params["num_tasks"]
    num_cores = validated_params["num_cores"]
    num_islands = validated_params["num_islands"]
    num_generations = validated_params["num_generations"]
    migration_interval = validated_params["migration_interval"]
    migration_rate = validated_params["migration_rate"]
    mutation_rate = validated_params["mutation_rate"]

    # Log the received inputs for debugging
    logging.info(f"Inputs received: Num Tasks={num_tasks}, "
                 f"Num Cores={num_cores}, Num Islands={num_islands}, "
                 f"Num Generations={num_generations}, "
                 f"Migration Interval={migration_interval}, "
                 f"Migration Rate={migration_rate}, "
                 f"Mutation Rate={mutation_rate}")

    # Generate task execution times (optional, if needed)
    task_times = generate_task_times(num_tasks)

    # Generate one random mapping per island
    islands_population = {
        island: [generate_individual(num_tasks, num_cores)]
        for island in range(num_islands)
    }

    logging.info("Population initialized successfully.")

    fitness_scores = []

    # Generational process
    for generation in range(1, num_generations + 1):
        logging.info(f"Generation {generation}:")
        generation_fitness_scores = []

        # Apply mutation
        for island_id in islands_population:
            islands_population[island_id] = [mutate(individual, mutation_rate, num_cores - 1) for individual in islands_population[island_id]]

        # Apply migration at defined intervals
        if generation % migration_interval == 0:
            islands_population = migrate(islands_population, migration_rate)

        # Send each mapping to fitnessTrigger for evaluation
        for island_id, island in islands_population.items():
            for individual in island:
                response = send_to_fitness({
                    "task_times": task_times,
                    "mapping": individual,
                    "num_cores": num_cores
                })
                if response:
                    generation_fitness_scores.append(response["fitness"])
                else:
                    logging.error(f"Failed to get fitness for individual: {individual}")

        # Store the fitness scores for the generation
        fitness_scores.append(generation_fitness_scores)
        logging.info(f"Fitness scores for generation {generation}: {generation_fitness_scores}")

    # Prepare the results for display
    results = {
        "message": "Evolution process completed successfully",
        "params": validated_params,
        "fitness_scores": fitness_scores,  # Fitness scores for each generation
        "final_population": islands_population,
        "task_times": task_times
    }

    # Return results as a response
    return func.HttpResponse(
        json.dumps(results),
        status_code=200,
        mimetype="application/json"
    )

@app.route(route="fitnessTrigger", auth_level="anonymous")
def fitnessTrigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        # Parse the request body
        req_body = req.get_json()
        logging.info(f"Received request body: {req_body}")

        # Extract parameters
        task_times = req_body.get('task_times')
        mapping = req_body.get('mapping')
        num_cores = req_body.get('num_cores')

        # Validate input
        if not all([task_times, mapping, num_cores]):
            return func.HttpResponse(
                "Missing required parameters. Please provide task_times, mapping, and num_cores.",
                status_code=400
            )

        # Ensure num_cores is a positive integer
        try:
            num_cores = int(num_cores)
            if num_cores <= 0:
                return func.HttpResponse(
                    "num_cores must be a positive integer.",
                    status_code=400
                )
        except (ValueError, TypeError):
            return func.HttpResponse(
                "num_cores must be a valid integer.",
                status_code=400
            )

        # Ensure mapping values are valid (0 <= core < num_cores)
        if any(core < 0 or core >= num_cores for core in mapping):
            return func.HttpResponse(
                f"Invalid mapping: core indices must be between 0 and {num_cores - 1}.",
                status_code=400
            )

        # Calculate fitness
        core_times = [0] * num_cores
        for task, core in enumerate(mapping):
            core_times[core] += task_times[task]
        total_time = max(core_times)
        fitness = 1 / total_time

        response_body = {
            "message": "Fitness calculated successfully",
            "core_times": core_times,
            "total_time": total_time,
            "fitness": fitness
        }
        logging.info(f"Response body: {response_body}")

        # Return JSON response
        return func.HttpResponse(
            json.dumps(response_body),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return func.HttpResponse(
            f"An error occurred: {e}",
            status_code=500
        )

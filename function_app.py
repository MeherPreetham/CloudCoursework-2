import azure.functions as func
import logging
import random
import json

app = func.FunctionApp()

# Generate random task execution times (1 to 10 units)
def generate_task_times(num_tasks):
    return [random.randint(1, 10) for _ in range(num_tasks)]

# Generate an individual chromosome (task-to-core mapping)
def generate_individual(num_tasks, num_cores):
    """Generate a 1D array where position = task and value = assigned core."""
    return [random.randint(0, num_cores - 1) for _ in range(num_tasks)]

def initialize_population(NUM_TASKS, NUM_CORES, NUM_ISLANDS):
    islands = {}
    for i in range(NUM_ISLANDS):
        # Generate only one chromosome (task-to-core mapping) per island
        chromosome = [random.randint(0, NUM_CORES - 1) for _ in range(NUM_TASKS)]
        islands[i] = chromosome  # Store exactly one solution per island
    return islands

@app.route(route="population", auth_level="anonymous")
def init_population(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    # Initialize parameters with default values (None or zero)
    population_size = req.params.get('population_size')
    num_cores = req.params.get('num_cores')
    num_islands = req.params.get('num_islands')
    island_pop = req.params.get('island_pop')
    num_generations = req.params.get('num_generations')
    migration_interval = req.params.get('migration_interval')
    migration_rate = req.params.get('migration_rate')

    try:
        # Validate that all required parameters are provided
        if not all([population_size, num_cores, num_islands, island_pop, num_generations, migration_interval, migration_rate]):
            return func.HttpResponse(
                "Missing required parameters. Please ensure all parameters are provided.",
                status_code=400
            )

        # Convert the parameters to the correct types (int or float)
        population_size = int(population_size)
        num_cores = int(num_cores)
        num_islands = int(num_islands)
        island_pop = int(island_pop)
        num_generations = int(num_generations)
        migration_interval = int(migration_interval)
        migration_rate = float(migration_rate)

        # Validate that the values are within acceptable ranges
        if population_size <= 0:
            return func.HttpResponse("Population size must be greater than zero.", status_code=400)
        if num_cores <= 0:
            return func.HttpResponse("Number of cores must be greater than zero.", status_code=400)
        if num_islands <= 0:
            return func.HttpResponse("Number of islands must be greater than zero.", status_code=400)
        if island_pop <= 0:
            return func.HttpResponse("Population per island must be greater than zero.", status_code=400)
        if num_generations <= 0:
            return func.HttpResponse("Number of generations must be greater than zero.", status_code=400)
        if migration_interval <= 0:
            return func.HttpResponse("Migration interval must be greater than zero.", status_code=400)
        if not (0 <= migration_rate <= 1):
            return func.HttpResponse("Migration rate must be between 0 and 1.", status_code=400)

        # Log the received inputs for debugging
        logging.info(f"Inputs received: Population Size={population_size}, "
                     f"Num Cores={num_cores}, Num Islands={num_islands}, "
                     f"Population Per Island={island_pop}, "
                     f"Num Generations={num_generations}, "
                     f"Migration Interval={migration_interval}, "
                     f"Migration Rate={migration_rate}")

    except ValueError as ve:
        # Handle the case where parameter conversion fails or invalid sample size
        logging.error(f"ValueError: {ve}")
        return func.HttpResponse(str(ve), status_code=400)
    except Exception as e:
        # Catch any unexpected errors
        logging.error(f"An unexpected error occurred: {e}")
        return func.HttpResponse("An unexpected error occurred while processing your request.", status_code=500)

  # Generate population for each island
    islands_population = {island: [generate_individual(population_size, num_cores) for _ in range(island_pop)] for island in range(num_islands)}

    logging.info("Population initialized successfully.")

    # Return JSON response
    return func.HttpResponse(
        json.dumps({"message": "Population initialized", "islands": islands_population}),
        status_code=200,
        mimetype="application/json"
    )
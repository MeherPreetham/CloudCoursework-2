import azure.functions as func
import logging
import json

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

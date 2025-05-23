import json
from typing import List, Dict, Any, Union, Optional
from openai import OpenAI
from pydantic import BaseModel, ValidationError
from bica.utils.utilities import *
from typing import Type


class GPTHandler:
    def __init__(self):
        api_key = get_environment_variable("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key)

    def generate_response(self, prompt: Union[str, Dict[str, Any]], compiled_data: Dict[str, Any] = None, **kwargs) -> Union[str, Dict[str, Any], BaseModel]:
        """
        Generate a response from the GPT model.

        :param prompt: The input prompt (required) - can be a string or a dictionary
        :param compiled_data: Optional compiled data to be used as message content
        :param kwargs: Additional optional parameters (e.g., model, temperature, functions, json_schema)
        :return: Generated response, function call information, or structured JSON
        """
        # Default parameters
        params = {
            "model": "gpt-4o-2024-08-06",
            "temperature": 0.7,
        }

        # Update with any provided kwargs
        params.update(kwargs)

        # Handle the prompt/messages
        if compiled_data:
            params["messages"] = [{"role": "user", "content": json.dumps(compiled_data)}]
        elif isinstance(prompt, str):
            params["messages"] = [{"role": "user", "content": prompt}]
        elif isinstance(prompt, dict) and "messages" in prompt:
            params["messages"] = prompt["messages"]
        else:
            raise ValueError("Invalid prompt format. Expected string, dict with 'messages', or compiled_data.")

        # Handle special parameters
        functions = params.pop('functions', None)
        json_schema = params.pop('json_schema', None)

        if functions:
            params['functions'] = functions
            params['function_call'] = 'auto'  # Helps the AI decide if there even is an appropriate function call

        if json_schema:
            params['messages'].insert(0, {"role": "system", "content": "You must respond with JSON output."})
            params['functions'] = [{
                "name": "output_json",
                "description": "Output JSON in the specified format",
                "parameters": json_schema
            }]
            params['function_call'] = {"name": "output_json"}

        try:
            response = self.client.chat.completions.create(**params)
            return self._process_response(response)
        except Exception as e:
            raise Exception(f"Error generating response: {str(e)}")

    def _process_response(self, response):
        """
        Process the API response.
        """
        message = response.choices[0].message

        if hasattr(message, 'function_call') and message.function_call:
            if message.function_call.name == "output_json":
                return json.loads(message.function_call.arguments)
            return {
                "type": "function_call",
                "function": message.function_call.name,
                "arguments": json.loads(message.function_call.arguments)
            }
        return message.content.strip()

    def generate_character_profile(self, prompt: str, schema: Type[BaseModel]) -> BaseModel:
        response = self.generate_response(prompt)
        try:
            return schema.parse_raw(response)
        except ValidationError as e:
            print(f"Validation error: {e}")
            # Return the raw response if validation fails
            return response


def main():
    """
    Extensive testing of the GPTHandler with various configurations.
    """
    handler = GPTHandler()

    # Define multiple functions for testing
    functions = [
        {
            "name": "get_weather",
            "description": "Get the weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "The city and state, e.g. San Francisco, CA"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                },
                "required": ["location", "unit"],
                "additionalProperties": False
            }
        },
        {
            "name": "calculate_mortgage",
            "description": "Calculate monthly mortgage payment",
            "parameters": {
                "type": "object",
                "properties": {
                    "principal": {"type": "number", "description": "The loan amount"},
                    "interest_rate": {"type": "number", "description": "Annual interest rate (percentage)"},
                    "loan_term": {"type": "number", "description": "Loan term in years"}
                },
                "required": ["principal", "interest_rate", "loan_term"],
                "additionalProperties": False
            }
        },
        {
            "name": "recommend_movie",
            "description": "Recommend a movie based on genre and year",
            "parameters": {
                "type": "object",
                "properties": {
                    "genre": {"type": "string", "description": "Movie genre"},
                    "year": {"type": "integer", "description": "Release year"}
                },
                "required": ["genre", "year"],
                "additionalProperties": False
            }
        }
    ]

    # Define JSON schema for structured output
    person_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "occupation": {"type": "string"},
            "hobbies": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["name", "age", "occupation", "hobbies"],
        "additionalProperties": False
    }

    # Test cases
    test_cases = [
        {
            "name": "Simple text output",
            "prompt": "Tell me a joke about programming.",
            "params": {}
        },
        {
            "name": "Function calling (weather)",
            "prompt": "What's the weather like in Tokyo?",
            "params": {"functions": functions}
        },
        {
            "name": "Function calling (mortgage)",
            "prompt": "Calculate the monthly mortgage payment for a $300,000 loan at 3.5% interest for 30 years.",
            "params": {"functions": functions}
        },
        {
            "name": "Function calling (movie recommendation)",
            "prompt": "Recommend a sci-fi movie from 2020.",
            "params": {"functions": functions}
        },
        {
            "name": "Structured JSON output (person profile)",
            "prompt": "Generate a profile for a fictional software developer.",
            "params": {"json_schema": person_schema}
        },
        {
            "name": "Custom temperature (high)",
            "prompt": "Write a short, creative story about a time-traveling robot.",
            "params": {"temperature": 0.9}
        },
        {
            "name": "Custom temperature (low)",
            "prompt": "Explain the concept of recursion in programming.",
            "params": {"temperature": 0.2}
        },
        {
            "name": "Combined function calling and custom parameters",
            "prompt": "What will the weather be like in New York next week? Be creative in your response.",
            "params": {"functions": functions, "temperature": 0.8, "max_tokens": 100}
        }
    ]

    # Run tests
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"Prompt: {test['prompt']}")
        try:
            response = handler.generate_response(test['prompt'], **test['params'])
            print("Response:", response)
        except Exception as e:
            print(f"Error occurred: {str(e)}")
        print("-" * 50)


if __name__ == "__main__":
    main()

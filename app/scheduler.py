# scheduling logic
import json
import time
import requests
from typing import List, Dict, Optional

# --- Ollama Configuration ---
# NOTE: Switched back to 'mistral' as this is the model the user successfully downloaded.
OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "mistral"
MAX_DEBATE_ROUNDS = 5  # Limit the number of turns

# --- Negotiation Data Structures ---

# Define the structured output format the agents MUST use for their proposals.
PROPOSAL_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "proposal_summary": {"type": "STRING",
                             "description": "A one-sentence summary of the agent's current proposal."},
        "proposed_schedule": {
            "type": "ARRAY",
            "description": "The current schedule being proposed or agreed upon, listing days and hours.",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "agent": {"type": "STRING", "enum": ["AgentA", "AgentB"]},
                    "day": {"type": "STRING", "enum": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]},
                    "hours": {"type": "STRING",
                              "description": "The block of time proposed for the agent, e.g., '9:00 AM - 1:00 PM'"},
                    "total_hours": {"type": "INTEGER", "description": "The calculated total hours for this shift."}
                }
            }
        },
        "response_to_opponent": {"type": "STRING",
                                 "description": "The agent's conversational response (agree, counter, or reject)."},
        "deal_status": {"type": "STRING", "enum": ["CONTINUE", "AGREED", "DEADLOCK"],
                        "description": "The negotiation status: CONTINUE if debating, AGREED if settled, DEADLOCK if stuck."}
    },
    "required": ["proposal_summary", "proposed_schedule", "response_to_opponent", "deal_status"]
}


# --- Core Constraint Logic (Your Solver Tool) ---

def check_global_constraints(schedule: List[Dict]) -> bool:
    """
    Checks if the proposed schedule satisfies all hard, non-negotiable company constraints.
    """
    daily_coverage = {day: [] for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]}
    total_hours = {"AgentA": 0, "AgentB": 0}

    # Constraint 2: The IT desk must be covered from 9:00 AM to 5:00 PM (Hard Constraint)
    MIN_COVERAGE_HOURS_PER_DAY = 8

    for shift in schedule:
        agent_id = shift['agent']
        hours = shift.get('total_hours', 0)
        day = shift['day']

        total_hours[agent_id] += hours

        # Simple check for coverage (assuming total hours per day must meet minimum)
        daily_coverage[day].append(hours)

    # Hard Constraint Check: Total coverage per day
    for day, hours_list in daily_coverage.items():
        daily_total = sum(hours_list)
        if daily_total < MIN_COVERAGE_HOURS_PER_DAY:
            print(
                f"⚠️ VIOLATION: {day} only has {daily_total} hours of coverage. Minimum is {MIN_COVERAGE_HOURS_PER_DAY}.")
            return False

    # Check the negotiable constraint (Max 25 hours per person)
    for agent, hours in total_hours.items():
        if hours > 25:
            print(f"⚠️ VIOLATION: {agent} has {hours} hours. Max desired is 25.")
            # We return True here to allow the debate to continue,
            # but this check gives the referee agent grounds to reject the deal.

    return True  # All hard constraints passed


# --- LLM Communication Logic ---

def call_ollama_api(system_instruction: str, history: List[Dict]) -> Optional[Dict]:
    """
    Makes the structured POST request to the local Ollama service.
    """
    headers = {'Content-Type': 'application/json'}

    # Ollama uses a simplified history format, combining system and chat history.
    history_str = "\n".join([f"--- {msg['role'].upper()} ---\n{msg['content']}" for msg in history])

    # Combine system instruction and history into the final prompt
    full_prompt = (
        f"{system_instruction}\n\n"
        f"--- CONVERSATION HISTORY ---\n{history_str}\n\n"
        f"Based on the history, provide your next move as a single JSON object "
        f"that strictly adheres to the schema provided in your instructions. "
        f"DO NOT include any text, markdown, or commentary outside of the JSON."
    )

    # Ollama payload
    payload = {
        "model": MODEL_NAME,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            # Use a low temperature for more deterministic, negotiation-focused responses
            "temperature": 0.2,
            "format": "json"
        }
    }

    print(f"--- Sending request to Ollama for {MODEL_NAME} move... ---")

    for attempt in range(4):
        try:
            response = requests.post(OLLAMA_API_URL, headers=headers, data=json.dumps(payload),
                                     timeout=60)  # Increased timeout for local LLM inference
            response.raise_for_status()

            result = response.json()
            json_text = result.get('response', '').strip()

            # Clean up and parse the JSON response
            json_text = json_text.replace('```json', '').replace('```', '').strip()

            return json.loads(json_text)

        except requests.exceptions.RequestException as e:
            print(f"Local Ollama connection failed (Attempt {attempt + 1}/4): {e}")
            if 'ConnectionRefusedError' in str(e):
                print("\nCRITICAL: Ollama app may not be running or not accessible at port 11434.")
                break
            if attempt < 3:
                delay = 2 ** attempt
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("Max retries reached. Exiting API call.")
                return None
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON response from Ollama. Raw Text: {json_text[:200]}...")
            print("This often means the local LLM failed to produce valid JSON.")
            return None
    return None


# --- Agent Initialization ---

def create_system_prompt(agent_name: str, goal: str, constraints: str) -> str:
    """Creates the detailed system instruction for an agent."""
    json_schema_str = json.dumps(PROPOSAL_SCHEMA, indent=2)

    return f"""
    You are {agent_name}, an expert scheduler agent. Your single goal is to secure a schedule for your client based on the following preference: {goal}.

    You must negotiate with your opponent, who has their own competing preference.

    Hard System Constraints (Non-Negotiable):
    {constraints}

    Negotiation Rules:
    1. Your proposal must reflect the *entire* schedule (both agents' shifts).
    2. Analyze the opponent's previous turn (if any).
    3. If the combined schedule meets your goal AND the hard constraints, set 'deal_status' to "AGREED".
    4. If it is unacceptable, adjust the 'proposed_schedule' and set 'deal_status' to "CONTINUE".
    5. Respond ONLY with a single JSON object that STRICTLY matches this schema.

    REQUIRED JSON SCHEMA:
    {json_schema_str}
    """


def setup_agents(global_constraints: str):
    """Defines the two competing agents."""

    # Agent A's Preferences (Goal 1)
    goal_a = "Client A prefers 20 hours of work per week, specifically focusing  on Monday, Tuesday, and Wednesday."
    prompt_a = create_system_prompt("AgentA", goal_a, global_constraints)

    # Agent B's Preferences (Goal 2)
    goal_b = "Client B prefers 20 hours of work per week, specifically focusing on Thursday and Friday."
    prompt_b = create_system_prompt("AgentB", goal_b, global_constraints)

    return [
        {"name": "AgentA", "system_prompt": prompt_a, "goal": goal_a, "call_func": call_ollama_api},
        {"name": "AgentB", "system_prompt": prompt_b, "goal": goal_b, "call_func": call_ollama_api},
    ]


# --- Main Simulation Loop ---

def run_negotiation_simulation():
    """Manages the turn-based debate between AgentA and AgentB."""

    # Two hard constraints for the PoC
    global_constraints = (
        "C1: The IT Desk must be staffed for a total of 8 hours every weekday (Monday-Friday).\n"
        "C2: Neither agent can be scheduled for more than 8 consecutive hours in a single day."
    )

    agents = setup_agents(global_constraints)
    history: List[Dict] = []

    print(f"--- Starting Two-Agent Schedule Negotiation with Local Model: {MODEL_NAME} ---")
    print(f"Global Constraints: \n{global_constraints}\n")

    # Initial Prompt: Kick off the debate by asking Agent A to propose the first full schedule.
    initial_message = (
        f"Start the negotiation. Propose a complete 5-day schedule that meets your client's goal ({agents[0]['goal']}) "
        f"while adhering to the hard constraints. The opponent agent (AgentB) will respond next."
    )

    # Set initial message in history for Agent A to respond to
    history.append({"role": "user", "content": initial_message})

    current_agent_index = 0
    final_schedule = None

    for round_num in range(1, MAX_DEBATE_ROUNDS + 1):

        current_agent = agents[current_agent_index]

        print(f"\n--- ROUND {round_num} - {current_agent['name']}'s Turn ---")

        # 1. Call the LLM to generate the move
        response_data = current_agent['call_func'](current_agent['system_prompt'], history)

        if not response_data:
            print("Simulation failed due to local LLM or JSON error.")
            break

        # 2. Extract structured and conversational parts
        schedule = response_data.get('proposed_schedule', [])
        status = response_data.get('deal_status', 'CONTINUE')
        summary = response_data.get('proposal_summary', 'No summary provided.')
        dialogue = response_data.get('response_to_opponent', 'No dialogue provided.')

        print(f"LLM Dialogue: {dialogue}")
        print(f"Proposal: {summary}")

        # 3. Add the agent's structured turn to history for the opponent to see
        history.append({"role": "model", "content": json.dumps(response_data)})

        # 4. Check status and constraints
        if status == "AGREED":

            if check_global_constraints(schedule):
                print("\n✅ SUCCESS: Agents AGREED on a schedule that passes all HARD CONSTRAINTS!")
                final_schedule = schedule
                break
            else:
                # If agents agree but the schedule is invalid, force them to CONTINUE or DEADLOCK
                print(
                    "\n❌ AGENT MISCALCULATION: Agents agreed, but the schedule VIOLATES hard constraints. Forcing continuation.")
                history.append({"role": "user",
                                "content": "SYSTEM REJECTED PROPOSAL: The agreed schedule violates hard system constraints (refer to the constraints section). You must continue negotiating and submit a valid schedule."})

        elif status == "DEADLOCK":
            print("\n🛑 DEADLOCK: Agents could not reach an agreement within the complexity limits.")
            break

        elif round_num == MAX_DEBATE_ROUNDS:
            print("\n🛑 ROUND LIMIT REACHED: Ending negotiation without agreement.")
            break

        # 5. Prepare for the next turn
        current_agent_index = 1 - current_agent_index  # Switch turns

    # --- Final Output ---
    if final_schedule:
        print("\n================ FINAL SCHEDULE RESULT ================")
        print(f"Global Constraints: {global_constraints}")
        print("-" * 50)

        total_hours_a = sum(s.get('total_hours', 0) for s in final_schedule if s['agent'] == 'AgentA')
        total_hours_b = sum(s.get('total_hours', 0) for s in final_schedule if s['agent'] == 'AgentB')

        print(f"AgentA (Goal: 20hrs) secured: {total_hours_a} hours")
        print(f"AgentB (Goal: 20hrs) secured: {total_hours_b} hours")
        print("-" * 50)

        # Display the formatted schedule
        for shift in sorted(final_schedule, key=lambda x: x['day']):
            print(
                f"| {shift['day']:<10} | {shift['agent']:<7} | {shift['hours']:<20} | {shift['total_hours']:<3} hrs |")

        print("=======================================================")
    else:
        print("\nNo valid schedule was agreed upon. See negotiation history above.")


if __name__ == "__main__":
    run_negotiation_simulation()

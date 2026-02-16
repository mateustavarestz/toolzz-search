import asyncio
import base64
from src.core.ai_processor import AIProcessor
from src.models.agent import AgentState

async def main():
    # 1. Create a dummy screenshot (1x1 pixel white image)
    # Valid 5x5 red pixel PNG
    dummy_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="
    
    # 2. Mock AgentState
    state = AgentState(
        step_index=1,
        current_url="http://example.com",
        title="Example Domain",
        text_excerpt="Example Domain\nThis domain is for use in illustrative examples in documents. You may use this domain in literature without prior coordination or asking for permission.",
        html_excerpt="<html><body><h1>Example Domain</h1></body></html>",
        screenshot_base64=dummy_b64,
        last_error=None
    )
    
    # 3. Instantiate AIProcessor
    # Ensure OPENAI_API_KEY is in .env or environment
    try:
        processor = AIProcessor()
        # processor.model = "gpt-4o"  # Override removed
        print("AIProcessor instantiated.")
    except Exception as e:
        print(f"Error instantiating AIProcessor: {e}")
        return

    # 4. Call plan_next_action
    print("calling plan_next_action...")
    try:
        action = await processor.plan_next_action(state, goal="Find more information")
        print("Action received:")
        print(action.model_dump_json(indent=2))
    except Exception as e:
        print(f"Error in plan_next_action: {e}")

if __name__ == "__main__":
    asyncio.run(main())

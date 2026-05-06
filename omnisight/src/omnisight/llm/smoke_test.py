from src.omnisight.llm.factory import make_llm_client, get_model_name
from src.omnisight.settings import settings


def main() -> None:
    print("=" * 60)
    print("OmniSight LLM Smoke Test")
    print("=" * 60)
    print(f"APP_NAME      : {settings.APP_NAME}")
    print(f"APP_ENV       : {settings.APP_ENV}")
    print(f"LLM_PROVIDER  : {settings.LLM_PROVIDER}")
    print(f"MODEL         : {get_model_name()}")
    print("=" * 60)

    client = make_llm_client()
    model = get_model_name()

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": "Say hello from OmniSight setup test."},
            ],
            temperature=0.2,
        )

        answer = response.choices[0].message.content
        print("Model response:")
        print(answer)

    except Exception as e:
        print("Smoke test failed.")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
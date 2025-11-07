import os
import openai
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")

openai.api_key = OPENAI_API_KEY

def retrieve_context(user_query):
    search_response = openai.vector_stores.search(
        vector_store_id=VECTOR_STORE_ID,
        query=user_query,
        max_num_results=20,
    )
    results = search_response.data
    context_texts = [" ".join([c.text for c in item.content]) if isinstance(item.content, list) else item.content for item in results if item.content]
    return "\n".join(context_texts)


def main():
    # Crear una nueva conversación
    conversation = openai.conversations.create()

    conversation_id = conversation.id
    print(f"🟢 Conversación iniciada (ID): {conversation_id}")

    while True:
        user_input = input("👤 Tú: ")
        if user_input.lower() in ["salir", "exit", "quit"]:
            break

        context = retrieve_context(user_input)

        # Enviar input al modelo
        response = openai.responses.create(
            model="gpt-5-codex",
            input=[
                {"role": "system", "content": f"Contexto recuperado:\n{context}"},
                {"role": "user", "content": user_input},
            ],
            conversation=conversation_id
        )

        print("🤖 Asistente:", response.output_text)


if __name__ == "__main__":
    main()
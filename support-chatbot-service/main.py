from app.llm.chat_model import chat_with_model
from app.llm.generate_embeddings import get_text_embedding
from app.llm.store_vectors import store_embedding
from app.llm.setup_supabase import setup_supabase
from app.llm.test_connection import test_bedrock_connection
from app.utils.logger.logger_util import get_logger
import sys

logger = get_logger()

def chat_mode():
    """Handle chat mode"""
    logger.info("=== CHAT MODE ===")
    print("\nWelcome to Chat Mode!")
    print("Type 'quit' to exit chat mode")
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            break
            
        if not user_input:
            continue
            
        try:
            # response = chat_with_model(user_input)
            response = chat_with_model(user_input, use_rag=True)
            print(f"\nAssistant: {response}")
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
            print("Sorry, I encountered an error. Please try again.")

def embedding_mode():
    """Handle embedding generation mode"""
    logger.info("=== EMBEDDING MODE ===")
    
    # 1. Test connection
    if not test_bedrock_connection():
        return
    
    # 2. Setup Supabase
    collection = setup_supabase()
    
    print("\nWelcome to Embedding Mode!")
    print("Enter Q&A pairs to generate embeddings (type 'done' to finish)")
    
    while True:
        # Get question
        question = input("\nQuestion (or 'done' to finish): ").strip()
        
        if question.lower() in ['done', 'exit', 'quit']:
            break
            
        if not question:
            continue
        
        # Get answer
        answer = input("Answer: ").strip()
        
        if not answer:
            print("Answer cannot be empty. Skipping...")
            continue
        
        # Generate embedding
        full_text = f"Q: {question}\nA: {answer}"
        logger.info(f"Text to vectorize:\n{full_text}")
        
        embedding = get_text_embedding(full_text)
        
        if embedding:
            store_embedding(collection, full_text, embedding)
            print("✓ Vector stored successfully!")
        else:
            logger.error("Failed to generate embedding")
            print("✗ Failed to generate embedding")

def show_menu():
    """Display the main menu"""
    print("\n" + "="*50)
    print("       LLM APPLICATION MENU")
    print("="*50)
    print("1. Chat with the AI model")
    print("2. Generate embeddings (Q&A storage)")
    print("3. Exit")
    print("="*50)
    
    choice = input("Please choose an option (1-3): ").strip()
    return choice

def main():
    """Main application entry point"""
    logger.info("Application started")
    
    print("Testing Bedrock connection...")
    if not test_bedrock_connection():
        logger.error("Bedrock connection test failed. Exiting.")
        return
    
    while True:
        choice = show_menu()
        
        if choice == '1':
            chat_mode()
        elif choice == '2':
            embedding_mode()
        elif choice == '3':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()
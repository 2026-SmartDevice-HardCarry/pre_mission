import os
import time
import logging
from dotenv import load_dotenv
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed

# 0. 환경 변수 로드 (.env 파일의 내용을 읽어옴)
load_dotenv()

# 1. 로깅 설정 (콘솔 및 파일 저장)
if not os.path.exists('evidence'):
    os.makedirs('evidence')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("evidence/m1_log.txt", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MiniMaxChatClient:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("MINIMAX_API_KEY")
        
        # 1. URL을 'minimaxi'로 유지
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.minimaxi.chat/v1",
        )
        
        self.history = [
            {"role": "system", "content": "너는 현관 거울 속의 루틴 관리자야. 짧고 명확하게 대답해."}
        ]
        self.max_history = 10 

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def get_response(self, user_input):
        self.history.append({"role": "user", "content": user_input})
        
        if len(self.history) > (self.max_history * 2 + 1):
            self.history = [self.history[0]] + self.history[-(self.max_history * 2):]

        # start_time 변수를 try 블록 밖으로 꺼냈습니다.
        start_time = time.time() 
        try:
            response = self.client.chat.completions.create(
                model="minimax-text-01", # 성공한 모델명으로 고정
                messages=self.history,
                timeout=10.0 
            )
            latency = (time.time() - start_time) * 1000

            answer = response.choices[0].message.content
            usage = response.usage
            
            logger.info(f"User: {user_input}")
            logger.info(f"AI: {answer}")
            logger.info(f"Usage: Prompt {usage.prompt_tokens}, Completion {usage.completion_tokens}, Total {usage.total_tokens}")
            logger.info(f"Latency: {latency:.2f}ms")
            
            self.history.append({"role": "assistant", "content": answer})
            print(f"\n[AI]: {answer}") # 터미널에도 대답이 보이게 추가
            return answer

        except Exception as e:
            logger.error(f"API 호출 중 오류 발생: {e}")
            raise e

def main():
    try:
        chat_client = MiniMaxChatClient()
        print("\n=== Routine Tracker Mirror Chat (M1) ===")
        print("대화를 시작합니다. (종료: exit / quit)\n")

        while True:
            user_input = input("[나]: ")
            if user_input.lower() in ['exit', 'quit']:
                print("프로그램을 종료합니다.")
                break
                
            if not user_input.strip():
                continue

            chat_client.get_response(user_input)
            
    except Exception as e:
        print(f"초기화 실패: {e}")

if __name__ == "__main__":
    main()
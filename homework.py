import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='program.log',
    level=logging.INFO)

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
payload = {'from_date': 1666782330}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения, которые необходимы для работы программы."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True
    else:
        logging.critical(f'Нет необходимых данных')


def send_message(bot, message):
    """отправляет сообщение в Telegram чат,
    определяемый переменной окружения TELEGRAM_CHAT_ID.
    Принимает на вход два параметра: экземпляр класса Bot
    и строку с текстом сообщения"""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение в чат {TELEGRAM_CHAT_ID}: {message}')
    except Exception as error:
        logging.error(f'Ошибка отправки сообщения в телеграмм: {error}')


def get_api_answer(timestamp):
    """делает запрос к единственному эндпоинту API-сервиса.\
        В качестве параметра в функцию передается временная метка.
        В случае успешного запроса должна вернуть ответ API,
        приведя его из формата JSON к типам данных Python"""
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except Exception as error:
        logging.error(f'Cервер Практикум.Домашка вернул ошибку: {error}')
        send_message(f'Cервер Практикум.Домашка вернул ошибку: {error}')
    if response.status_code != HTTPStatus.OK:
        status_code = response.status_code
        logging.error(f'Ошибка {status_code}')
        raise Exception(f'Ошибка {status_code}')
    return response.json()


def check_response(response):
    """проверяет ответ API на соответствие документации.
    В качестве параметра функция получает ответ API, приведенный к типам данных Python"""
    if isinstance(response, dict):
        if 'homeworks' in response:
            if isinstance(response['homeworks'], list):
                return response['homeworks']
            raise TypeError('Ответ API отличен от списка')
        raise KeyError('Ошибка словаря по ключу homeworks')
    raise TypeError('Ответ API отличен от словаря')


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой работы."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API ')
    if 'status' not in homework:
        raise Exception('Отсутствует ключ "status" в ответе API ')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        logging.error(f'Неопределенный статус работы: {homework_status}')
        raise Exception(f'Неопределенный статус работы: {homework_status}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logging.info('Бот работает')
    if check_tokens():
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        timestamp = int(time.time())
        while True:
            try:
                response = get_api_answer(timestamp)
                answer = check_response(response)
                logging.info('Список домашек получен')
                if len(answer) > 0:
                    send_message(bot, parse_status(answer[0]))
                    timestamp = response['current_date']
                else:
                    logging.info('Новых уведомлений нет')
                time.sleep(RETRY_PERIOD)
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                logging.error(message)
                time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()

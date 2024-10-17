import requests
from bs4 import BeautifulSoup
import re
import g4f
import streamlit as st
from g4f.client import Client

client = Client()

SYSTEM_PROMPT = """
Проскорь кандидата, насколько он подходит для данной вакансии.

Сначала напиши, на русском языке, короткий анализ, который будет пояснять оценку.
Отдельно оцени качество заполнения резюме (понятно ли, с какими задачами сталкивался кандидат и каким образом их решал?). Эта оценка должна учитываться при выставлении финальной оценки - нам важно нанимать таких кандидатов, которые могут рассказать про свою работу.
Потом представь результат в виде оценки от 1 до 10 на русском языке.
""".strip()

def request_gpt(system_prompt, user_prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=1000,
        temperature=0,
    )

    if response.choices:
        return response.choices[0].message.content
    else:
        return "Нет ответа от модели."

def get_html(url: str):
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
            },
        )
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при получении данных: {e}")
        return None

def extract_job_data(html):
    soup = BeautifulSoup(html, 'html.parser')

    title_element = soup.find('h1', {'data-qa': 'vacancy-title'})
    title = title_element.text.strip() if title_element else "Название вакансии не указано"

    company_element = soup.find('a', {'data-qa': 'vacancy-company-name'})
    company = company_element.text.strip() if company_element else "Компания не указана"

    salary_element = soup.find('span', {'data-qa': 'vacancy-salary-compensation-type-net'})
    salary = salary_element.text.strip() if salary_element else "Зарплата не указана"

    experience_element = soup.find('span', {'data-qa': 'vacancy-experience'})
    experience = experience_element.text.strip() if experience_element else "Опыт не указан"

    employment_mode_element = soup.find('p', {'data-qa': 'vacancy-view-employment-mode'})
    employment_mode = employment_mode_element.text.strip() if employment_mode_element else "Тип занятости не указан"

    location_element = soup.find('p', {'data-qa': 'vacancy-view-location'})
    location = location_element.text.strip() if location_element else "Местоположение не указано"

    description_element = soup.find('div', {'data-qa': 'vacancy-description'})
    description = description_element.text.strip() if description_element else "Описание не указано"

    responsibilities, requirements, conditions = "", "", ""

    if description:
        responsibilities_match = re.search(r'Обязанности:(.*?)(Требования:|Условия:|$)', description, re.DOTALL)
        requirements_match = re.search(r'Требования:(.*?)(Условия:|$)', description, re.DOTALL)
        conditions_match = re.search(r'Условия:(.*?)($)', description, re.DOTALL)

        if responsibilities_match:
            responsibilities = responsibilities_match.group(1).strip()
        if requirements_match:
            requirements = requirements_match.group(1).strip()
        if conditions_match:
            conditions = conditions_match.group(1).strip()

    skills_section = soup.find('div', {'data-qa': 'skills-table'})
    skills = [skill.text.strip() for skill in skills_section.find_all('span', {'data-qa': 'bloko-tag__text'})] if skills_section else []

    return {
        "title": title,
        "company": company,
        "salary": salary,
        "experience": experience,
        "employment_mode": employment_mode,
        "location": location,
        "description": description,
        "responsibilities": responsibilities,
        "requirements": requirements,
        "conditions": conditions,
        "skills": skills
    }

def extract_candidate_data(html):
    soup = BeautifulSoup(html, 'html.parser')

    name_element = soup.find('h2', {'data-qa': 'bloko-header-1'})
    name = name_element.text.strip() if name_element else "Имя не указано"

    gender_age_element = soup.find('p')
    gender_age = gender_age_element.text.strip() if gender_age_element else "Пол и возраст не указаны"

    location_element = soup.find('span', {'data-qa': 'resume-personal-address'})
    location = location_element.text.strip() if location_element else "Местоположение не указано"

    job_title_element = soup.find('span', {'data-qa': 'resume-block-title-position'})
    job_title = job_title_element.text.strip() if job_title_element else "Должность не указана"

    job_status_element = soup.find('span', {'data-qa': 'job-search-status'})
    job_status = job_status_element.text.strip() if job_status_element else "Статус поиска работы не указан"

    experience_section = soup.find('div', {'data-qa': 'resume-block-experience'})
    experience_items = experience_section.find_all('div', class_='resume-block-item-gap') if experience_section else []

    experiences = []

    for item in experience_items:
        period_elem = item.find('div', class_='bloko-column_s-2')
        duration_elem = item.find('div', class_='bloko-text')

        period = period_elem.text.strip() if period_elem else ""
        duration = duration_elem.text.strip() if duration_elem else ""

        period_with_duration = period.replace(duration, f" ({duration})") if duration else period

        company_elem = item.find('div', class_='bloko-text_strong')
        position_elem = item.find('div', {'data-qa': 'resume-block-experience-position'})
        description_elem = item.find('div', {'data-qa': 'resume-block-experience-description'})

        company = company_elem.text.strip() if company_elem else "Компания не указана"
        position = position_elem.text.strip() if position_elem else "Должность не указана"
        description = description_elem.text.strip() if description_elem else ""

        experiences.append(f"**{period_with_duration}**\n*{company}*\n**{position}**\n{description}\n")

    skills_section = soup.find('div', {'data-qa': 'skills-table'})
    skills = [skill.text.strip() for skill in skills_section.find_all('span', {'data-qa': 'bloko-tag__text'})] if skills_section else []

    return {
        "name": name,
        "gender_age": gender_age,
        "location": location,
        "job_title": job_title,
        "job_status": job_status,
        "experiences": experiences,
        "skills": skills
    }

def main():
    st.title("Scoring Кандидатов")

    # Ввод URL вакансии
    job_description_url = st.text_area("Введите URL вакансии")

    # Ввод URL резюме
    cv_url = st.text_area("Введите URL резюме")

    # Кнопка для оценки резюме
    if st.button("Оценить резюме"):
        if job_description_url and cv_url:
            with st.spinner("Обработка данных..."):
                html_content_job = get_html(job_description_url)
                html_content_cv = get_html(cv_url)

                if html_content_job and html_content_cv:
                    job_data = extract_job_data(html_content_job)
                    candidate_data = extract_candidate_data(html_content_cv)

                    # Запрос к GPT для скоринга кандидата
                    user_prompt = f'Описание вакансии: {job_data["description"]}\nРезюме: {candidate_data["name"]}, {candidate_data["gender_age"]}, {candidate_data["location"]}'
                    score_response = request_gpt(SYSTEM_PROMPT, user_prompt)

                    # Вывод результата
                    st.write(score_response)
                else:
                    st.error("Не удалось получить данные из одного или обоих URL.")
        else:
            st.warning("Пожалуйста, заполните оба поля.")

if __name__ == "__main__":
  main()

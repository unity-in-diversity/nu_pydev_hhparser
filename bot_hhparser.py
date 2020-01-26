import requests
import datetime
import os
import pprint
from collections import defaultdict
import json

BASE_URL = 'https://api.hh.ru/'
URL_vacancies = f'{BASE_URL}vacancies'
url_areas = f'{BASE_URL}areas'
headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.79 Safari/537.36"}
all_areas_json = requests.get(url_areas, headers=headers).json()


def iter_dict(d, val, indices):
    for k, v in d.items():
        if k == val:
            yield indices + [k], v
        if isinstance(v, dict):
            yield from iter_dict(v, val.lower(), indices + [k])
        elif isinstance(v, list):
            yield from iter_list(v, val.lower(), indices + [k])

def iter_list(seq, key, indices):
    for k, v in enumerate(seq):
        if isinstance(v, dict):
            yield from iter_dict(v, key.lower(), indices + [k])
        elif isinstance(v, list):
            yield from iter_list(v, key.lower(), indices + [k])

def find_key(obj, key):
    if isinstance(obj, dict):
        yield from iter_dict(obj, key.lower(), [])
    elif isinstance(obj, list):
        yield from iter_list(obj, key.lower(), [])

def find_area_intindex(name, area_req):
    ncount = 0
    for n in name:
        ncount += 1
        nname = n[1]
        nname = nname.lower()
        if nname == area_req.lower():
            return ncount
    raise ValueError('Нет такого города')

def find_id_area(count, key):
    kcount = 0
    intid = count
    for k in key:
        kcount += 1
        if kcount == intid:
            return k
#arg1 передаем введеный город от юзера из бота
#получаем промежточный номер который передаем в другую функцию чтобы найти id города в hh
#можно проверять есть ли на hh такой город для поиска
def get_intcount_area(arg1):
    while True:
        area_req = arg1.lower()
        name = find_key(all_areas_json, 'name')
        try:
            count_area = find_area_intindex(name, area_req)
            return count_area
        except ValueError:
            #print('Город введен с ошибкой, повторите ввод:')
            return 0

def get_id_area(intcount_area):
    key = find_key(all_areas_json, 'id')
    dict_area = find_id_area(intcount_area, key)
    id_area = dict_area[1]
    return id_area

def get_vacancies_url(count_pages, url, text_req, id_area):
    all_vacancies_urls = []
    for page in range(count_pages):
        params = {'text': text_req, 'area': id_area, 'page': page}
        result = requests.get(url, params=params).json()
        all_vacancies_urls.append([{'api_url': item['url']} for item in result['items']])
    return all_vacancies_urls

#print('Выбран город', area_req, 'id -', id_area)
#text_req = input('Введите ключевые слова для поска вакансии: ')

def get_req(arg1, arg2):
    '''
    :arg1 = из бота город
    :arg2 = из бота ключевая фраза
    :return = параметры для запроса к апи (текст, и город)
    '''
    intcount_area = get_intcount_area(arg1)
    id_area = get_id_area(intcount_area)
    text_req = arg2
    return id_area, text_req

def get_reqs_params(id_area, text_req):
    params = {'text': text_req, 'area': id_area}
    return params

def compare_file_create_date(filename):
    today = str(datetime.date.today())
    fd = os.path.getctime(filename)
    fd = str(datetime.datetime.fromtimestamp(fd))
    filedate = fd[0:10]
    if filedate == today:
        return True
    else:
        return False

def process(id_area, text_req, params, area_req, qtop=20):
    global request_history
    result = requests.get(URL_vacancies, headers=headers, params=params).json()
    count_vacancies = result['found']
    #items_vacancies = result['items']
    count_pages = result['pages']

    #print('СТРАНИЦ', count_pages)
    #print('ВАКАНСИЙ', count_vacancies)
    #if not count_vacancies:
    #    return False

    allurls = get_vacancies_url(count_pages, URL_vacancies, text_req, id_area)
    count_url_skils = 0
    key_skills = defaultdict(int)
    salary_list = []
    for url_vacancy in allurls:
        for url in url_vacancy:
            url_req_vac = url['api_url']
            one_vacancy = requests.get(url_req_vac).json()
            for skil in one_vacancy['key_skills']:
                skill_name = skil['name']
                key_skills[skill_name] += 1
            salary = one_vacancy['salary']
            if salary is not None:
                salary_to = salary.get('to')
                if salary_to is not None:
                    salary_list.append(salary_to)
            count_url_skils += 1

    sum_salary_count = int(sum(salary_list)/len(salary_list))
    sorted_key_skills = sorted(key_skills.items(), key=lambda x: int(x[1]), reverse=True)
    filename = str(area_req)+'_'+str(text_req)

    #загружаем json с историей запросов
    with open(filename+'.json', 'w', encoding='utf8') as file:
        json.dump(sorted_key_skills, file, ensure_ascii=False)

    #формируем строки для внесения в историю запросов
    #key_h - ключ словаря запрос_код региона, file_h = имя файла с результатом запроса
    key_h = text_req + '_' + id_area
    file_h = str(filename)+'.json'

    #загружаем json с историей запросов в переменную, добавялем новый запрос
    with open('request_history.json', encoding='utf-8') as file:
        data = json.load(file)
    data[key_h] = file_h

    #выгружаем обратно в json обновленный словарь с историей запросов
    with open('request_history.json', mode='w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False)

    #request_history[key_h] = str(filename)+'.json'
    #with open('request_history.json', 'w', encoding='utf8') as file:
    #    json.dump(request_history, file, ensure_ascii=False)

    #print(request_history)
    print('Всего вакансий', count_vacancies)
    print('Средняя зарплата', sum_salary_count)
    print('Отсортирвоанный список навыков по частоте упоминания в вакансиях:\n')

    top_vacancies = []
    for i in range(qtop):
        top_vacancies.append(sorted_key_skills[i])
    print([x for x in top_vacancies], sep=",")

# def load_result_from_file(file, data):
#     now = datetime.datetime.now()
#
#     if date

arg1 = 'омск'
arg2 = 'сисадмин'
if get_intcount_area(arg1):
    id_area, text_req = get_req(arg1, arg2)
    params = get_reqs_params(id_area, text_req)
    process(id_area, text_req, params, arg1)
else:
    print('ошибка при вводе города')
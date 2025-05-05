import pandas as pd
import json
from pathlib import Path
import numpy as np
import re

pd.set_option('display.max_rows', None)
pd.set_option('display.max_column', None)

with open(Path(__file__).resolve().parent / './config.json', encoding='utf-8') as f:
    config = json.load(f)


class Transformer:
    def transform(self, df, distr, month):

        function_mapping = {
            "find_most_matches_column": self.find_most_matches_column,
            "find_most_matches_header": self.find_most_matches_header,
            "find_word_matches_column": self.find_word_matches_column,
            "find_header": self.find_header,
            "find_numeric_column_with_length_matches": self.find_numeric_column_with_length_matches,
            "find_filtered_word_matches_column": self.find_filtered_word_matches_column
        }

        df = self.define_header_and_clean_rows(df)
        df = self.clear_excess_columns(df)
        df = self.clear_excess_rows(df)

        new_df = pd.DataFrame()

        for column in config["columns_config"]:
            func = function_mapping[column["function"]]
            if len(column["config_key"]) == 1:
                result = func(df, config[column["config_key"][0]]['items'])
            else:
                result = func(df, config[column["config_key"][0]]['items'], config[column["config_key"][1]]['items'])
            if result:
                # print(column["new_column"], result)
                new_df[column["new_column"]] = df[result]
            else:
                new_df[column["new_column"]] = np.nan


        new_df['Дистрибьютор'] = distr
        new_df['Месяц'] = month


        new_df = self.update_address_column(new_df)

        if new_df["Клиент"].isna().all():  # Если ВСЕ значения NaN
            fio_columns = self.find_fio_columns(df)  # Ищем столбец с ФИО
            if fio_columns:  # Если нашли хотя бы один такой столбец
                new_df["Клиент"] = df[fio_columns[0]]  # Берем первый найденный столбец


        if not new_df["ИНН клиента"].isna().all():
            new_df[['ИНН клиента', 'Штрихкод продукта']] = new_df[['ИНН клиента', 'Штрихкод продукта']].astype(str)

        return new_df

    def clear_excess_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Удаляет столбцы, которые полностью состоят из NaN

        """
        columns_to_drop = [
            column_index for column_index in range(df.shape[1])
            if df.iloc[:, column_index].isna().all()]
        df.drop(df.columns[columns_to_drop], axis=1, inplace=True)
        return df

    def clear_excess_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Удаляет строки, которые полностью состоят из NaN

        """
        rows_to_drop = [
            row_index for row_index in range(df.shape[0])
            if df.iloc[row_index, :].isna().all()
        ]
        df.drop(rows_to_drop, axis=0, inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def count_nan_before_first_value(self, df):
        """
        Подсчитывает количество NaN ячеек в каждом столбце до первой ненулевой (не NaN).

        """
        nan_counts = {}
        for column in df.columns:
            column_data = df[column]
            # Считаем количество NaN до первой не NaN
            count = 0
            for value in column_data:
                if pd.isna(value):
                    count += 1
                else:
                    break
            nan_counts[column] = count
        return nan_counts

    def define_header_and_clean_rows(self, dataframe):
        """
        Найти первую строку с числовым значением, установить для каждого столбца
        в качестве заголовка первое не NaN значение из строк выше, удалить строки выше.
        """
        header_indices = {}  # Словарь для хранения индексов заголовков для каждого столбца

        # Определяем индекс строки, где начинаются числовые данные
        start_index = None
        for i, row in dataframe.iterrows():
            if any(
                    isinstance(cell, (int, float)) and not pd.isna(cell) or  # Числовые значения
                    (isinstance(cell, str) and cell.replace(",", "").replace(".", "").isdigit())  # Строковые числа
                    for cell in row
            ):
                start_index = i
                break

        if start_index is None:
            raise ValueError("Не удалось найти строку с числовыми значениями.")

        # Ищем заголовок для каждого столбца с приоритетом строк, ближе к start_index
        for col in dataframe.columns:
            for i in range(start_index - 1, -1, -1):  # Двигаемся от строки с данными вверх
                if not pd.isna(dataframe[col].iloc[i]):
                    header_indices[col] = i
                    break

        # Формируем новый заголовок для таблицы
        new_headers = [
            dataframe[col].iloc[header_indices[col]] if col in header_indices else col
            for col in dataframe.columns
        ]

        # Создаем очищенный DataFrame
        cleaned_dataframe = dataframe.iloc[start_index:].reset_index(drop=True)
        cleaned_dataframe.columns = new_headers

        return cleaned_dataframe

    def find_most_matches_column(self, df, keywords):
        """
            Найти столбец с наибольшим количеством совпадений со списком ключевых слов.

            """
        max_matches = 0
        best_column = None

        for column in df.columns:
            # Подсчитываем количество совпадений в текущем столбце
            matches = 0
            for value in df[column]:
                if pd.notna(value):
                    lowered_value = str(value).lower()
                    if any(keyword in lowered_value for keyword in keywords):
                        matches += 1

            if matches > max_matches:
                max_matches = matches
                best_column = column

        if max_matches < len(df) / 2:
            return None

        return best_column

    def find_header(self, dataframe, keywords):
        """
        Найти название столбца, в котором заголовок содержитя полностью в списке ключевых слов.

        """
        target_column = None
        # print(dataframe.columns)
        for column in dataframe.columns:
            for keyword in keywords:
                # print(column)
                # print(keyword)
                if column == keyword:
                    target_column = column
                    return target_column
        return target_column

    def find_most_matches_header(self, dataframe, keywords):
        """
        Найти название столбца, в котором заголовок содержит наибольшее количество совпадений
        со списком ключевых слов.

        """
        max_matches = 0
        best_column = None

        for column in dataframe.columns:
            header = str(column).lower()
            matches = sum(keyword in header for keyword in keywords)

            if matches > max_matches:
                max_matches = matches
                best_column = column

        return best_column

    def find_word_matches_column(self, dataframe, keywords):
        """
        Найти столбец с наибольшим количеством совпадений со списком ключевых слов,
        сравнивая каждое слово в строке.

        Args:
            dataframe (pd.DataFrame): Исходный DataFrame.
            keywords (list): Список ключевых слов для проверки.

        Returns:
            str: Название столбца с наибольшим количеством совпадений.
        """
        max_matches = 0
        best_column = None

        for column in dataframe.columns:
            # Пропускаем столбцы, где нет буквенных значений
            if not dataframe[column].apply(
                    lambda x: isinstance(x, str) and any(c.isalpha() and "а" <= c <= "я" for c in x.lower())).any():
                continue

            # Подсчитываем количество совпадений в текущем столбце
            matches = 0
            for value in dataframe[column]:
                if pd.notna(value):
                    cleaned_value = str(value).replace(",", " ").replace(".", " ").lower()
                    words = [word.strip() for word in cleaned_value.split()]
                    if any(word in keywords for word in words):
                        matches += 1
            if matches > max_matches:
                max_matches = matches
                best_column = column

        if max_matches < len(dataframe) / 2:
            return None

        return best_column

    def find_numeric_column_with_length_matches(self, dataframe, lengths):
        """
        Найти столбец, где строки содержат только цифры, и длина этих строк соответствует одной из переданных длин.

        """
        max_matches = 0
        best_column = None

        for column in dataframe.columns:
            matches = 0
            for value in dataframe[column]:
                if pd.notna(value):
                    str_value = str(value).strip()  # Убираем пробелы
                    if str_value.isdigit() and len(str_value) in lengths:
                        matches += 1

            if matches > max_matches:
                max_matches = matches
                best_column = column

        if max_matches < len(dataframe) / 2:
            return None

        return best_column

    def find_filtered_word_matches_column(self, dataframe, include_keywords, exclude_keywords):
        """
        Найти столбец с наибольшим количеством совпадений со списком ключевых слов,
        сравнивая каждое слово в строке, исключая строки с нежелательными словами.

        Args:
            dataframe (pd.DataFrame): Исходный DataFrame.
            include_keywords (list): Список ключевых слов, которые должны быть в строке.
            exclude_keywords (list): Список ключевых слов, при наличии которых строка не учитывается.

        Returns:
            str: Название столбца с наибольшим количеством совпадений.
        """
        max_matches = 0
        best_column = None

        for column in dataframe.columns:
            # Пропускаем столбцы, где нет буквенных значений
            if not dataframe[column].apply(
                    lambda x: isinstance(x, str) and any(c.isalpha() and "а" <= c <= "я" for c in x.lower())).any():
                continue

            # Подсчитываем количество совпадений в текущем столбце
            matches = 0
            for value in dataframe[column]:
                if pd.notna(value):
                    cleaned_value = str(value).replace(",", "").replace(".", "").lower()
                    words = [word.strip() for word in cleaned_value.split()]
                    if any(word in include_keywords for word in words) and not any(
                            word in exclude_keywords for word in words):
                        matches += 1

            if matches > max_matches:
                max_matches = matches
                best_column = column

        if max_matches < len(dataframe) / 2:
            return None

        return best_column

    def update_address_column(self, dataframe):
        """
        Если столбец "Адрес полностью" совпадает с "Область/ Край", "Город" или "Улица, номер дома",
        заменяет его на конкатенацию этих трех столбцов, если все они не пустые.

        Args:
            dataframe (pd.DataFrame): Исходный DataFrame.
        """
        cols = ["Область/Край", "Город", "Улица, номер дома"]
        dataframe["Адрес полностью"] = dataframe.apply(
            lambda row: ', '.join(filter(None, [row[col] for col in cols]))
            if row["Адрес полностью"] in row[cols].values and all(pd.notna(row[col]) and row[col] != '' for col in cols)
            else row["Адрес полностью"], axis=1
        )
        return dataframe

    def find_fio_columns(self, dataframe):
        """
        Найти столбцы, содержащие ФИО в формате 'Фамилия И.О.'.

        Args:
            dataframe (pd.DataFrame): Исходный DataFrame.

        Returns:
            list: Список названий столбцов, содержащих ФИО.
        """
        fio_pattern = re.compile(r'^[А-ЯЁ][а-яё]+ [А-ЯЁ]\.[А-ЯЁ]\.$')  # Регулярное выражение для ФИО
        fio_columns = []

        for column in dataframe.columns:
            matches = 0
            total_values = dataframe[column].count()  # Количество непустых строк

            for value in dataframe[column].dropna():  # Проход только по непустым строкам
                if fio_pattern.match(str(value)):  # Проверяем каждое слово
                    matches += 1

            if matches > 10:
                fio_columns.append(column)

        return fio_columns

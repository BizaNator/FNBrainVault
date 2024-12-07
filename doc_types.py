from typing import Dict, List
from dataclasses import dataclass

class ChapterInfo:
    def __init__(self, number: int, title: str, start_page: int, end_page: int = 0):
        self.number = number
        self.title = title
        self.start_page = start_page
        self.end_page = end_page
        self.subsections = []

    def to_dict(self) -> dict:
        return {
            'number': self.number,
            'title': self.title,
            'start_page': self.start_page,
            'end_page': self.end_page,
            'subsections': self.subsections
        }

    @staticmethod
    def from_dict(data: dict) -> 'ChapterInfo':
        chapter = ChapterInfo(
            number=data['number'],
            title=data['title'],
            start_page=data['start_page'],
            end_page=data['end_page']
        )
        chapter.subsections = data.get('subsections', [])
        return chapter 
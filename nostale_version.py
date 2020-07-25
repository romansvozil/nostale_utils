from dataclasses import dataclass
from pefile import PE
from typing import List

import aiohttp
import asyncio
import hashlib


@dataclass
class ClientInfo:
    locale: str
    client_x_hash: str
    client_hash: str
    client_version: str


def get_version(data):
    pe = PE(data=data)
    info = pe.VS_FIXEDFILEINFO[0]
    return '.'.join(
        map(str,
            [info.FileVersionMS >> 16,
             info.FileVersionMS & 0xFFFF,
             info.FileVersionLS >> 16,
             info.FileVersionLS & 0xFFFF]))


def get_file_hash(data) -> str:
    return hashlib.md5(
        data,
    ).hexdigest()


class NostaleDownloader:
    FILES: str = 'https://spark.gameforge.com/api/v1/patching/download/' \
                 'latest/nostale/default?locale={locale}&architecture=x64&branchToken'
    CLIENT_X = 'NostaleClientX.exe'
    CLIENT = 'NostaleClient.exe'

    DOWNLOAD_URL = 'http://patches.gameforge.com'

    def __init__(self, locale: str):
        self._locale = locale
        self._files: List = []
        self._client_info = None

    @property
    def files_url(self):
        return self.FILES.format(locale=self._locale)

    async def fetch_files(self, session: aiohttp.ClientSession):
        async with session.get(self.files_url) as response:
            return (await response.json()).get('entries')

    @staticmethod
    async def download_file(session: aiohttp.ClientSession, url: str):
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.read()

    def filter_url_by_name(self, lst, name):
        return self.DOWNLOAD_URL + next(x for x in lst if x.get('file') == name).get('path')

    async def fetch_info(self):
        async with aiohttp.ClientSession() as session:
            entries = await self.fetch_files(session)
            client_x, client = await asyncio.gather(
                self.download_file(session, self.filter_url_by_name(entries, self.CLIENT_X)),
                self.download_file(session, self.filter_url_by_name(entries, self.CLIENT)))

        self._client_info = ClientInfo(self._locale,
                                       get_file_hash(client_x),
                                       get_file_hash(client),
                                       get_version(client))

    @property
    def client_info(self):
        return self._client_info

    @classmethod
    async def get_client_info(cls, locale) -> ClientInfo:
        downloader = cls(locale)
        await downloader.fetch_info()
        return downloader.client_info


if __name__ == '__main__':
    print(asyncio.run(NostaleDownloader.get_client_info('cs')))
    print(asyncio.run(NostaleDownloader.get_client_info('pl')))

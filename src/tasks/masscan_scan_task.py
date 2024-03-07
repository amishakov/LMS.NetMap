from .base_job import BaseJob, MessageObserver
from modules.masscan.executor import MasscanScanner
from modules.masscan.parser import XMLParser, JsonParser, ListParser, BaseMasscanParser, PortStructure, NetworkLink
from database.queries import Queries
from time import time
import traceback
import asyncio
from typing import Dict, Type, List, Tuple

class MasscanScanTask(BaseJob):
    
    def __init__(self, observer: MessageObserver, scheduler, name: str, task_id: int, arguments: dict, scanning_ip: str, scanning_mac: str, masscan_log_path: str, db: Queries):
        super().__init__(observer, scheduler, name)
        self._coro = self.run(db=db, task_id=task_id, arguments=arguments, scanning_ip=scanning_ip, scanning_mac=scanning_mac, masscan_log_path=masscan_log_path)
    
    async def _task_func(self, arguments: dict, masscan_log_path: str) -> str:
        """Запускает активное сканирование с использованием masscan-а

        Args:
            argumets (dict): параметры сканирования

        Returns:
            _type_: результат сканирования
        """
        masscan_obj = MasscanScanner(**arguments)
        return await masscan_obj.async_execute(log_path=masscan_log_path)
    
    async def _parser_results(self, format: str, input_data: str, scanning_ip: str, scanning_mac: str) -> Tuple[List[Type[PortStructure]], List[Type[NetworkLink]]]:
        parsers: Dict[str, Type[BaseMasscanParser]] = {
            'oX': XMLParser,
            'oJ': JsonParser,
            'oL': ListParser
        }
        parent_ip = scanning_ip
        loop = asyncio.get_event_loop()
        parser = parsers.get(format)
        return await loop.run_in_executor(None, parser.parse, input_data, parent_ip)
    
    def _write_result_to_db(self, db: Queries, port_result: List[Type[PortStructure]], link_result: List[Type[NetworkLink]]) -> None:
        """Метод парсинга результатов сканирования nmap-а и занесения в базу

        Args:
            db (Queries): объект запросов в базу
            iface (str): имя сетевого интерфейса
        """
        db.port.write_many(data=[i.to_dict() for i in port_result])
        db.l3link.write_many(data=[i.to_dict() for i in link_result])
        
    async def run(self, db: Queries, task_id: int, arguments: dict, scanning_ip: str, scanning_mac: str, masscan_log_path: str):
        """Метод выполнения задачи
        1. Произвести операции согласно методу self._task_func
        2. Записать результаты в базу согласно методу self._write_result_to_db
        3. Попутно менять статут задачи

        Args:
            db (Queries): объект запросов к базе
            task_id (int): идентификатор задачи
        """
        db.task.set_pending_status(index=task_id)
        try:
            t1 = time()
            arguments['interface_addr'] = scanning_ip
            result = await self._task_func(arguments=arguments, masscan_log_path=masscan_log_path)
            ports, links = await self._parser_results(format=arguments.get('format', 'oJ'), input_data=result, scanning_ip=scanning_ip)
            self.logger.debug('Task func "%s" finished after %.2f seconds', self.__class__.__name__, time() - t1)
            self._write_result_to_db(db=db, port_result=ports, link_result=links)
            self.logger.debug('Result of task "%s" wrote to db', self.__class__.__name__)
        except Exception as e:
            self.logger.error('Task "%s" failed with error\n%s', self.__class__.__name__, traceback.format_exc())
            db.task.set_failed_status(index=task_id, error_message=traceback.format_exc())
            raise e
        db.task.set_finished_status(index=task_id)
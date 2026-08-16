import asyncio
import logging
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian
from .const import KEBA_PORT, KEBA_UNIT_ID

_LOGGER = logging.getLogger(__name__)

class KebaHub:
    def __init__(self, hass, host):
        self._hass = hass
        self._host = host
        # Verbindung über TCP Port 502
        self._client = AsyncModbusTcpClient(host=self._host, port=KEBA_PORT)
        self._lock = asyncio.Lock()

    async def connect(self):
        await self._client.connect()

    async def disconnect(self):
        await self._client.close()

    async def read_uint32_register(self, address: int) -> int:
        """Liest ein UINT32 Register (2 Words) mittels FC3."""
        async with self._lock:
            try:
                # FC3 (Read), Unit ID 255
                result = await self._client.read_holding_registers(
                    address=address, count=2, slave=KEBA_UNIT_ID
                )
                if result.isError():
                    _LOGGER.error(f"Fehler beim Lesen des Registers {address}")
                    return None
                
                decoder = BinaryPayloadDecoder.fromRegisters(
                    result.registers, byteorder=Endian.BIG, wordorder=Endian.LITTLE
                )
                return decoder.decode_32bit_uint()
            except Exception as e:
                _LOGGER.error(f"Modbus Lese-Fehler: {e}")
                return None

    async def write_uint16_register(self, address: int, value: int):
        """Schreibt ein UINT16 Register mittels FC6."""
        async with self._lock:
            try:
                # FC6 (Write Single Register), Unit ID 255
                result = await self._client.write_register(
                    address=address, value=value, slave=KEBA_UNIT_ID
                )
                if result.isError():
                    _LOGGER.error(f"Fehler beim Schreiben des Registers {address}")
            except Exception as e:
                _LOGGER.error(f"Modbus Schreib-Fehler: {e}")

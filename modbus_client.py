"""
Modbus RTU Client untuk PLC Omron
Program ini digunakan untuk membaca dan menulis data register dari PLC Omron
menggunakan protokol Modbus RTU melalui serial port.
"""

from pymodbus.client.sync import ModbusSerialClient
import time
import json
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


import random

class OmronModbusClient:
    """Class untuk mengelola komunikasi Modbus dengan PLC Omron"""
    
    def __init__(self, config_file='config.json'):
        """
        Inisialisasi Modbus client
        
        Args:
            config_file (str): Path ke file konfigurasi JSON
        """
        self.config = self._load_config(config_file)
        self.client = None
        
    def _load_config(self, config_file):
        """Load konfigurasi dari file JSON"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_file} tidak ditemukan, menggunakan default config")
            return self._default_config()
    
    def _default_config(self):
        """Konfigurasi default"""
        return {
            "port": "COM3",
            "baudrate": 9600,
            "parity": "E",
            "stopbits": 1,
            "bytesize": 8,
            "timeout": 1,
            "unit_id": 1
        }
    
    def connect(self):
        """Membuat koneksi ke PLC"""
        try:
            self.client = ModbusSerialClient(
                method='rtu',
                port=self.config['port'],
                baudrate=self.config['baudrate'],
                parity=self.config['parity'],
                stopbits=self.config['stopbits'],
                bytesize=self.config['bytesize'],
                timeout=self.config['timeout']
            )
            
            if self.client.connect():
                logger.info(f"Berhasil terhubung ke PLC di {self.config['port']}")
                return True
            else:
                logger.error("Gagal terhubung ke PLC")
                return False
        except Exception as e:
            logger.error(f"Error saat koneksi: {e}")
            return False
    
    def disconnect(self):
        """Menutup koneksi ke PLC"""
        if self.client:
            self.client.close()
            logger.info("Koneksi ke PLC ditutup")
    
    def read_holding_register(self, address, count=1):
        """
        Membaca Holding Register (HR)
        
        Args:
            address (int): Alamat register (contoh: 12 untuk HR12)
            count (int): Jumlah register yang dibaca
            
        Returns:
            list: Nilai register atau None jika error
        """
        try:
            unit_id = self.config.get('unit_id', 1)
            result = self.client.read_holding_registers(address, count, unit=unit_id)
            
            if result.isError():
                logger.error(f"Error membaca HR{address}: {result}")
                return None
            else:
                logger.info(f"Berhasil membaca HR{address}: {result.registers}")
                return result.registers
        except Exception as e:
            logger.error(f"Exception saat membaca register: {e}")
            return None
    
    def write_holding_register(self, address, value):
        """
        Menulis ke Holding Register (HR)
        
        Args:
            address (int): Alamat register (contoh: 12 untuk HR12)
            value (int): Nilai yang akan ditulis (0-65535)
            
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        try:
            unit_id = self.config.get('unit_id', 1)
            result = self.client.write_register(address, value, unit=unit_id)
            
            if result.isError():
                logger.error(f"Error menulis HR{address}: {result}")
                return False
            else:
                logger.info(f"Berhasil menulis nilai {value} ke HR{address}")
                return True
        except Exception as e:
            logger.error(f"Exception saat menulis register: {e}")
            return False
    
    def read_input_register(self, address, count=1):
        """
        Membaca Input Register (IR)
        
        Args:
            address (int): Alamat register
            count (int): Jumlah register yang dibaca
            
        Returns:
            list: Nilai register atau None jika error
        """
        try:
            unit_id = self.config.get('unit_id', 1)
            result = self.client.read_input_registers(address, count, unit=unit_id)
            
            if result.isError():
                logger.error(f"Error membaca IR{address}: {result}")
                return None
            else:
                logger.info(f"Berhasil membaca IR{address}: {result.registers}")
                return result.registers
        except Exception as e:
            logger.error(f"Exception saat membaca input register: {e}")
            return None
    
    def read_coil(self, address, count=1):
        """
        Membaca Coil (bit output)
        
        Args:
            address (int): Alamat coil
            count (int): Jumlah coil yang dibaca
            
        Returns:
            list: Nilai coil (True/False) atau None jika error
        """
        try:
            unit_id = self.config.get('unit_id', 1)
            result = self.client.read_coils(address, count, unit=unit_id)
            
            if result.isError():
                logger.error(f"Error membaca Coil {address}: {result}")
                return None
            else:
                logger.info(f"Berhasil membaca Coil {address}: {result.bits[:count]}")
                return result.bits[:count]
        except Exception as e:
            logger.error(f"Exception saat membaca coil: {e}")
            return None
    
    def write_coil(self, address, value):
        """
        Menulis ke Coil (bit output)
        
        Args:
            address (int): Alamat coil
            value (bool): Nilai yang akan ditulis (True/False)
            
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        try:
            unit_id = self.config.get('unit_id', 1)
            result = self.client.write_coil(address, value, unit=unit_id)
            
            if result.isError():
                logger.error(f"Error menulis Coil {address}: {result}")
                return False
            else:
                logger.info(f"Berhasil menulis nilai {value} ke Coil {address}")
                return True
        except Exception as e:
            logger.error(f"Exception saat menulis coil: {e}")
            return False

    def send_random_pulse(self):
        """
        Mengirim nilai random (1-9) ke D100 dan pulse ke CIO 100.00
        CIO 100.00 diasumsikan di alamat Coil 1600 (100 x 16 + 0)
        """
        try:
            # 1. Generate dan kirim Random Integer ke D100
            rand_val = random.randint(1, 9)
            print(f"\n[LOGIC] Mengirim nilai random {rand_val} ke D100...")
            self.write_holding_register(100, rand_val)
            
            # 2. Kirim Pulse High ke CIO 100.00 (Coil 1600)
            # Asumsi Mapping: CIO 0.00 = Coil 0 -> CIO 100.00 = 100*16 + 0 = 1600
            cio_100_00_addr = 1600 
            print(f"[LOGIC] Mengirim Pulse HIGH ke CIO 100.00 (Coil {cio_100_00_addr})...")
            self.write_coil(cio_100_00_addr, True)
            
            # 3. Delay sesaat
            time.sleep(0.5)
            
            # 4. Kirim Pulse Low ke CIO 100.00
            print(f"[LOGIC] Mengirim Pulse LOW ke CIO 100.00 (Coil {cio_100_00_addr})...")
            self.write_coil(cio_100_00_addr, False)
            
            print("[LOGIC] Selesai.")
            
        except Exception as e:
            logger.error(f"Error saat random pulse: {e}")


def main():
    """Fungsi utama - Interaktif Trigger Pulse"""
    
    # Inisialisasi client
    plc = OmronModbusClient('config.json')
    
    # Koneksi ke PLC
    if not plc.connect():
        logger.error("Tidak dapat terhubung ke PLC. Program dihentikan.")
        return
    
    try:
        print("\n=== Program Trigger Data Random & Pulse ===")
        print("Setiap Enter akan mengirim:")
        print(" -> Nilai Random (1-9) ke D100")
        print(" -> Pulse High (0.5s) ke CIO 100.00 (Coil 1600)")
        
        while True:
            cmd = input("\nTekan [ENTER] untuk kirim data (ketik 'q' untuk keluar): ")
            if cmd.lower() == 'q':
                print("Keluar program...")
                break
            
            # Jalankan logika pulse
            plc.send_random_pulse()
            
    except KeyboardInterrupt:
        print("\n\nProgram dihentikan oleh user")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        # Tutup koneksi
        plc.disconnect()


if __name__ == "__main__":
    main()

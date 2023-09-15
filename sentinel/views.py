from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from sentinelhub import SHConfig
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
from datetime import datetime, timedelta
import json
import subprocess
import tarfile
import shutil
from django.core.files.images import ImageFile        
from rest_framework.permissions import IsAuthenticated, AllowAny

import os
import urllib.request
            
import rasterstats
import shapefile
from osgeo import gdal

from .serializers import GeometryImmobileWithoutPropertiesSerializer, GeometryDistrictWithoutPropertiesSerializer, GeometryBorderWithoutPropertiesSerializer, PropertieImmobileSerializer
from .models import GeometryCoordinatesUTM, GeometryBorder, GeometryDistrict, GeometryImmobile, DistrictImagesNDVISub, DistrictImageRGB, ImmobileImageRGB, NDVIStatistics
from django.http import JsonResponse

from django.shortcuts import render
from django.conf import settings


class GetPropertieView(APIView):
    pass                       

class GetFeauresView(APIView):
    pass         

class SentinelRequests():
    """
    Possui métodos de:
      - autenticação com o satélite Sentinel Hub;
      - requisição de imagens NDVI para o satélite Sentinel Hub;
      - requisição de imagens RGB para o satélite Sentinel Hub;
      - conversão de coordenada de imagens;
      - recorte de imagens utilizando shapefile;
      - criação de arquivos shapefile montados a partir de coordenadas GEO;
      - criação de arquivos shapefile montados a partir de coordenadas UTM;
      - criação de bound box (bbox) a partir de coordenadas;
      - descompactação de arquivos e busca por metadados;
    """
    bbox=''
    date_start=''
    date_end=''
    token=''
    filename=''

    def __del__(self):
        """
        Limpa variável global que representa o token da requisição ao sentinel.
        """
        self.token = ''       

    def convert_image_coordinates(self):
        pass
    
    def cut_out(self, gid):
        pass
      
    def create_shapefile_geo(self, gid):
        pass

    def create_shapefile_utm(self, gid):
        pass

    def get_statistics(self, gid):
        pass   

    def search_data(self, name, path):
        """
        Lê arquivos JSON e procura pela com menor valor de cobertura de nuvem, pois foi essa escolhida na requisição.
        """
        with open(f"media/images/{path}/{name}") as file:
            data = json.load(file)

        lowest_cloud_coverage = data['scenes'][0]['tiles'][0]['cloudCoverage']
        date_request = data['scenes'][0]['tiles'][0]['date']
        
        for scene in data['scenes']:
            for tile in scene['tiles']:
                cloud_coverage = tile['cloudCoverage']
                if cloud_coverage < lowest_cloud_coverage:
                    lowest_cloud_coverage = cloud_coverage
                    date_request = tile['date']
        
        return date_request, lowest_cloud_coverage, data

    def unpack_tar_file(self, tar_file_path, tar_filename, path_destination, new_filename):
        """
        Descompacta um arquivo específico e o salva localmente renomeando-o.
        """
        try:
            with tarfile.open(tar_file_path, 'r') as tar_file:
                file = tar_file.extractfile(tar_filename)
                if file:
                    try:
                        with open(path_destination + '/' + new_filename, 'wb') as new_file:
                            shutil.copyfileobj(file, new_file)
                        print(f"\n*** Sucesso na descompactação do arquivo {new_filename}. ***\n")
                        return True
                    except:
                        print(f"\n*** Erro na descompactação do arquivo {new_filename}. ***\n")
                        return False
                else:
                    print(f"\n*** Erro na descompactação do arquivo {new_filename}. ***\n")
                    return False
        except:
            print(f"\n*** Erro na descompactação do arquivo {new_filename}. ***\n")
            return False

    def sentinel_image_request_rgb(self):
        pass

    def image_request_rgb(self):
        pass

    def sentinel_image_request_ndvi(self):
        """ 
        Requisição para API do Sentinel Hub através de comando curl, dados de entrada e saída são setados nesse comando. 
        Após a requisição uma imagem NDVI deve ser salva na pasta /media/files/output_ndvi
        """   

        """
        Requisição com parâmetros para se obter o NDVI.
        """
        request_ndvi = {
            "input": {
                "bounds": {
                    "properties": {
                        "crs": "http://www.opengis.net/def/crs/EPSG/0/32722"
                    },
                    "bbox": self.bbox
                },
                "data": [
                    {
                        "type": "sentinel-2-l2a",
                        "dataFilter": {
                            "timeRange": {
                                "from": self.date_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "to": self.date_end.strftime("%Y-%m-%dT%H:%M:%SZ")
                            }
                        },
                        "processing": {
                            "harmonizeValues": "true"       
                        },
                        "maxCloudCoverage": 0,
                    }
                ]
            },
            "output": {
                "resx": 10,
                "resy": 10, 
                "responses": [
                    {
                        "identifier": "default",
                        "format": {
                            "type": "image/tiff",
                            "quality": 80,
                        }
                    },
                    {
                        "identifier": "userdata",
                        "format": {
                            "type": "application/json"
                        }
                    }
                ],
                "upsampling": "NEAREST"
            }
        }

        evalscript_ndvi='''//VERSION=3
        function setup() {
            return{
                input: [
                    {
                        bands: ["B04", "B08"],
                        units: "REFLECTANCE"
                    }
                ],
                mosaicking: Mosaicking.ORBIT,
                output: {
                    id: "default",
                    bands: 1,
                    sampleType: SampleType.FLOAT32
                }
            }
        }

        function updateOutputMetadata(scenes, inputMetadata, outputMetadata) {
           outputMetadata.userData = { "scenes":  scenes.orbits }   
        }

        function evaluatePixel(sample) {
            let ndvi = (sample[0].B08 - sample[0].B04) / (sample[0].B08 + sample[0].B04)
            return [ ndvi ]
        }
        '''
    
        request = json.dumps(request_ndvi)
        
        curl_command = f'''curl -X POST \
        https://services.sentinel-hub.com/api/v1/process \
        -H 'Authorization: Bearer {self.token}' \
        -H 'accept: application/tar' \
        -F 'request={request}' \
        -F 'evalscript={evalscript_ndvi}' -o media/files/output_ndvi/{self.filename}.tar '''  #    
        # print(json.dumps(curl_command, indent=4))

        result = subprocess.run(curl_command, shell=True, capture_output=True)

        """
        Verifica se a requisição foi bem sucedida ou não, por exemplo, token expirado, portanto acesso negado.
        Não funciona pois a saída stdout vêm através do .tar
        """
        # stdout = result.stdout.decode('utf-8')
        # stdout = json.loads(stdout)
        # if stdout["error"]["status"] and stdout["error"]["status"] != 200:
        #     return False
        
        if result.returncode != 0:
            print(f"\n*** Erro na requisição do arquivo {self.filename}.tar ao Sentinel. ***\n.")
            # print(result)
            return False
        else:
            print(f"\n*** Sucesso na requisição do arquivo {self.filename}.tar ao Sentinel. ***\n.") 
            # print(result)
            return True

    def image_request_ndvi(self):
        """
        Ajusta dados do request e realiza requisição.
        """
        print(f"\n\n*** Data inicial: {self.date_start} ***\n*** Data final: {self.date_end} ***\n\n.") 

        if(not(self.sentinel_image_request_ndvi())): 
            # return False, f"Não foi possível realizar requisição de arquivo {self.filename}.tar ao Sentinel Hub."
            return False, f"Não foi possível realizar requisição de arquivo {self.filename}.tar ao Sentinel Hub."
        
        """
        Extrai arquivos da requisição.
        """
        if(not(self.unpack_tar_file(f"media/files/output_ndvi/{self.filename}.tar", "default.tif", "media/images/output_ndvi", f"IMAGE_{self.filename}.tif"))):
            return False, "Não foi possível realizar descompactação, arquivo não encontrado."
        
        if(not(self.unpack_tar_file(f"media/files/output_ndvi/{self.filename}.tar", "userdata.json", "media/images/output_ndvi", f"METADATA_{self.filename}.json"))):
            return False, "Não foi possível realizar descompactação, arquivo não encontrado."         
        
        return True, f"Sucesso na realização da requisição do arquivo {self.filename}."

    def get_bbox(self, coordinates, type):
        """
        Percorre todo array ou multi-array de coordenadas e monta o BBOX correspondente.
        """
        min_x = float("inf")
        min_y = float("inf")
        max_x = float("-inf")
        max_y = float("-inf")

        if type == "MultiPolygon":
            """ É um multipolígono """
            for polygon_1 in coordinates:
                for polygon in polygon_1:
                    for coordinate in polygon:
                        try:
                            x, y, z = coordinate
                        except:
                            x, y = coordinate
                        min_x = min(min_x, x)
                        min_y = min(min_y, y)
                        max_x = max(max_x, x)
                        max_y = max(max_y, y)
        else:
            """ É um polígono """
            for polygon_1 in coordinates:
                for coordinate in polygon_1:
                    try:
                        x, y, z = coordinate
                    except:
                        x, y = coordinate
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)

        self.bbox = [ min_x, min_y, max_x, max_y ]
    
    def search_coordinates_utm(self, id):
        """
        Busca coordenadas do Banco de Dados e monta o BBOX.
        """
        try:
            geometry = GeometryCoordinatesUTM.objects.get(id=id)
            self.get_bbox(geometry.geometry["coordinates"], geometry.geometry["type"])
            
            return True, "Coordenadas encontradas."
        except:
            return False, "Não foi possível encontrar coordenadas no Banco de Dados." 

    def search_coordinates_geo(self, id, checker=None):
        pass

    def sentinel_authentication(self):
        """
        Autenticação com API do Sentinel Hub, é necessário se cadastrar no site do Sentinel Hub, posteriormente obter um token.
        """
        client_id = settings.SENTINEL_CLIENT_ID
        client_secret = settings.SENTINEL_CLIENT_SECRET

        configuration = SHConfig()
        configuration.sh_client_id = client_id
        configuration.sh_client_secret = client_secret
        configuration.save()

        client = BackendApplicationClient(client_id=client_id)
        oauth = OAuth2Session(client=client)
        
        try:
            token = oauth.fetch_token(token_url="https://services.sentinel-hub.com/oauth/token", client_secret=client_secret)
        except:
            return False 

        """
        Verifica se o token foi obtido.
        """
        config = SHConfig()
        config.sh_client_id = client_id
        config.sh_client_secret = client_secret
        config.save()

        client = BackendApplicationClient(client_id=client_id)
        oauth = OAuth2Session(client=client)
        
        try:
            token = oauth.fetch_token(token_url="https://services.sentinel-hub.com/oauth/token", client_secret=client_secret)
        except:
            return False 

        self.token = token["access_token"]

        # resp = oauth.get("https://services.sentinel-hub.com/oauth/tokeninfo")
        return True  
    
class DetectChange(APIView, SentinelRequests):
    """
    Responsável por varrer todas propriedades, distrito por distrito, detectar alteração e informar ao frontend todas regiões detectadas. 
    """
    permission_classes = [IsAuthenticated]
    # permission_classes = [AllowAny]
        
    id=''
    response=[]
    districts=[]

    range_date_start_new=''
    range_date_end_new=''
    range_date_start_old=''
    range_date_end_old=''

    data_request_new='' 
    data_request_old=''
    metadados_new=''
    metadados_old=''

    def __init__(self):
        """
        Setando variáveis
        """
        self.districts = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]

        """
        Varrendo SEDE-CENTRO, dados que terão que ser DINÂMICOS posteriormente.
        """
        self.id = 13
        self.range_date_start_new = datetime(2023, 5, 16) # .strftime("%Y-%m-%dT%H:%M:%SZ")
        self.range_date_end_new = datetime(2023, 5, 30) # .strftime("%Y-%m-%dT%H:%M:%SZ")
        self.range_date_start_old = self.range_date_start_new
        self.range_date_end_old = self.range_date_end_new
    
    def detect_change(self):
        """
        Pegar todos gids e cordenadas referente ao distrito em execução.
        """
        if self.id == 12 or self.id == 13 or self.id == 14:
            """
            SEDE-NORTE, SEDE-CENTRO, SEDE-SUL devem referenciar SEDE
            """
            immobiles = GeometryImmobile.objects.filter(district_code=1, district_code_nickname=self.id, zone=None)
        else:
            immobiles = GeometryImmobile.objects.filter(district_code=self.id, zone=None)
        
        for immobile in immobiles:
            """
            Obtém dados estatísticos referente aquela propriedade em execução.
            """
            statistics = self.get_statistics(immobile.gid)
            if(not(statistics)):
                return False, "Não foi possível obter estatística."

            """
            Realiza comparação com valor de desvio padrão da subtração de pixels para detectar ou não alteração na imagem.
            """
            detected = False
            for statistic in statistics:
                if statistic["std"] and statistic["std"] < .194186:
                    detected = True
            
            """
            Salva novos dados estatísticos na tabela de imóveis
            """
            immobile.statistics = statistics
            immobile.detected = detected
            immobile.save()

            """
            Salva novos dados estatísticos na tabela de estatísticas
            """   
            # statistics_table = NDVIStatistics(
            #     gid=immobile.gid,
            #     date=self.data_request_new,
            #     statistics=statistics,
            # )
            # statistics_table.save()

        return True, "Sucesso no processo de varredura e detecção de imóveis em distritos."

    def first_rgb_image(self):
        pass

    def get_rgb_images(self, checker):
        pass
    
    def first_ndvi_image(self):
        """
        Realiza requisição de duas imagens NDVI (NEW e OLD).
        """
        
        """
        Busca coordenadas do Banco de Dados e monta o BBOX.
        """
        res, text = self.search_coordinates_utm(self.id)   
        if not(res):
            """
            Erro ao realizar requisição.
            """
            return res, text

        """
        Requisição NDVI_OLD
        """
        self.date_start = self.range_date_start_old
        self.date_end = self.range_date_end_old
        self.filename = "NDVI_OLD"
        res, text = self.image_request_ndvi()        
        if not(res):
            """
            Erro ao realizar requisição.
            """
            return res, text
        
        """
        Procura pelos metadados corretos no JSON da requisição NDVI_OLD.
        """
        self.data_request_old, cloud_coverage, self.metadados_old = self.search_data(f"METADATA_NDVI_OLD.json", "output_ndvi")

        """
        Verifica cobertura de nuvem.
        """
        if cloud_coverage > .2:
            self.date_adjustment_old(self, 5)
            return False, "Imagem disponível possui mais de 20 por cento de cobertura de nuvem, portanto foi recusada e as datas de busca foram incrementadas."

        """
        Requisição NDVI_NEW.
        """
        self.date_start = self.range_date_start_new
        self.date_end = self.range_date_end_new
        self.filename = "NDVI_NEW"
        res, text = self.image_request_ndvi()        
        if not(res):
            """
            Erro ao realizar requisição.
            """
            return res, text
        
        """
        Procura pelos metadados corretos no JSON da requisição NDVI_NEW.
        """
        self.data_request_new, cloud_coverage, self.metadados_new = self.search_data(f"METADATA_NDVI_NEW.json", "output_ndvi")

        """
        Verifica cobertura de nuvem.
        """
        if cloud_coverage > .2:
            self.date_adjustment_new(self, 5)
            return False, "Imagem disponível possui mais de 20 por cento de cobertura de nuvem, portanto foi recusada e as datas de busca foram incrementadas."
    
        return True, "Sucesso na primeira requisição de imagens NDVI."

    def get_ndvi_images(self):
        """
        Verifica se imagem existe no bucket, se sim baixar, senão realiza uma requisição a mais.
        """
        try:
            """
            Busca por última imagem no banco de dados.
            """
            latest_image = DistrictImagesNDVISub.objects.filter(district=self.id).latest('date_request_ndvi_new')
            url = latest_image.get_link_ndvi_new()

            """
            Baixar imagem IMAGE_NDVI_OLD do bucket. OBS.: PERMISSÃO AO BUCKET DEVER SER PÚBLICA
            """
            path = os.getcwd()
            urllib.request.urlretrieve(url, f"{path}/media/images/output_ndvi/IMAGE_NDVI_OLD.tif")
            
            print('\n--------------------\n', 'POSSUI IMAGEM NDVI NO BANCO', '\n--------------------\n')
            print(f"\n*** Sucesso na requisição de imagem ao bucket / à nuvem ***\n")

            """
            Busca coordenadas do Banco de Dados e monta o BBOX.
            """
            res, text = self.search_coordinates_utm(self.id)        
            if not(res):
                """
                Erro ao realizar requisição.
                """
                return res, text

            """
            Ajusta as datas.
            """
            self.date_adjustment_new(15)

            """
            Requisição NDVI_NEW.
            """
            self.date_start = self.range_date_start_new
            self.date_end = self.range_date_end_new
            self.filename = "NDVI_NEW"
            res, text = self.image_request_ndvi()        
            if not(res):
                """
                Erro ao realizar requisição.
                """
                return res, text
            
            """
            Procura pelos metadados corretos no JSON da requisição NDVI_NEW.
            """
            self.data_request_new, cloud_coverage, self.metadados_new = self.search_data(f"METADATA_NDVI_NEW.json", "output_ndvi")

            """
            Verifica cobertura de nuvem.
            """
            if cloud_coverage > .2:
                self.date_adjustment_new(self, 5)
                return False, "Imagem disponível possui mais de 20 por cento de cobertura de nuvem, portanto foi recusada e as datas de busca foram incrementadas."

            """
            Ajusta variáveis para serem salvas no banco de dados.
            """
            self.data_request_old = latest_image.date_request_ndvi_new
            self.metadados_old = latest_image.metadados_ndvi_new
            self.range_date_start_old=latest_image.range_date_start_new
            self.range_date_end_old=latest_image.range_date_end_new

        except:
            print('\n--------------------\n', 'NÃO POSSUI IMAGEM NDVI NO BANCO', '\n--------------------\n')
            """
            Realiza a primeira requisição.
            """
            
            ver, text = self.first_ndvi_image() 
            if ver:
                print(f"\n*** {text} ***\n")    
            else:
                return False, text   
        
        """
        Subtração NDVI.
        """
        if(not(self.ndvi_subtraction())):
            text = "Não foi possível realizar subtração de imagens. Formato de imagem inválido." 
            return Response({"info": text, "status": status.HTTP_400_BAD_REQUEST})

        """
        Salvar imagem(ns) no banco de dados.
        """
        print(f"\n*** Salvando dados ***\n")
        district = GeometryDistrict.objects.get(code=self.id)
        new_image = DistrictImagesNDVISub(
            district=district,
            range_date_start_new=self.range_date_start_new,
            range_date_end_new=self.range_date_end_new,
            range_date_start_old=self.range_date_start_old,
            range_date_end_old=self.range_date_end_old,
            date_request_ndvi_new=self.data_request_new, 
            date_request_ndvi_old=self.data_request_old, 
            metadados_ndvi_new = self.metadados_new,
            metadados_ndvi_old = self.metadados_old
        )
        new_image.link_ndvi_old.save(f"{self.id}_IMAGE_NDVI_OLD_{self.data_request_old}.tif", ImageFile(open('media/images/output_ndvi/IMAGE_NDVI_OLD.tif', 'rb')))
        new_image.link_ndvi_new.save(f"{self.id}_IMAGE_NDVI_NEW_{self.data_request_new}.tif", ImageFile(open('media/images/output_ndvi/IMAGE_NDVI_NEW.tif', 'rb')))
        new_image.link_ndvi_sub.save(f"{self.id}_IMAGE_NDVI_SUB_{self.data_request_new}.tif", ImageFile(open('media/images/output_ndvi/IMAGE_NDVI_SUB.tif', 'rb')))
        new_image.save()
        print(f"\n*** Dados salvos com sucesso ***\n")    
        
        return True, "Requisição de imanges NDVI finalizada."

    def date_adjustment_new(self, days):
        self.range_date_start_new = self.range_date_start_new + timedelta(days=days)    # incrementa mais X dias
        self.range_date_end_new = self.range_date_end_new + timedelta(days=days)        # incrementa mais X dias

    def date_adjustment_old(self, days):
        self.range_date_start_old = self.range_date_start_old + timedelta(days=days)    # incrementa mais X dias
        self.range_date_end_old = self.range_date_end_old + timedelta(days=days)        # incrementa mais X dias

    def get(self, request):
        """
        Ajusta as datas.
        """
        self.date_adjustment_new(15)

        """
        Realiza autenticação com API Sentinel Hub.
        """
        if(not(self.sentinel_authentication())):
            return Response({"info": "Não foi possível realizar autenticação ao Sentinel Hub.", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        
        """
        Percorre distrito por distrito
        """
        for self.district_code in self.districts:    
            # messages = []

            """
            Requisita imagens NDVI para comparação de dados estatísticos dos pixels. 
            """
            verification, text = self.get_ndvi_images()
            if not(verification):
                # messages.append(text)
                # continue
                return Response({ 'info': text, 'status': status.HTTP_500_INTERNAL_SERVER_ERROR, 'district_images': str(self.response)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            """
            Obtém dados estatísticos dos pixels da subtração de imagens NDVI e atualiza banco de dados. 
            """
            verification, text = self.detect_change()
            if not(verification):
                # messages.append(text)
                # continue
                return Response({ 'info': text, 'status': status.HTTP_500_INTERNAL_SERVER_ERROR, 'district_images': str(self.response)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            """
            Requisita imagens RGB para devolução ao frontend. 
            """
            verification, text = self.get_rgb_images("district")
            if not(verification):
                # messages.append(text)
                # continue
                return Response({ 'info': text, 'status': status.HTTP_500_INTERNAL_SERVER_ERROR, 'district_images': str(self.response)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            """
            Limpa variável global que representa o token da requisição ao sentinel.
            """
            self.__del__()
        
        """
        Prepara dados de resposta ao usuário e retorna ao frontend.
        """
        return Response({ 'info': "Sucesso nas modificações", 'status': status.HTTP_200_OK, 'district_images': str(self.response)}, status=status.HTTP_200_OK)
    
class GetImageRgb(DetectChange):
    pass

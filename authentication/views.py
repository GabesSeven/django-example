from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework.views import APIView


from .models import CustomUser
from .serializers import CustomUserCreateSerializer, CustomUserSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings

from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags


import time



class UserView(APIView):
    """
    Realiza CRUD de usuário comum e master.
    Somente usuário admin possuirá acesso a esta classe.
    """    
    permission_classes = [IsAuthenticated]

    def send_first_login_email(self, email, user):
        """
        Envia e-mail com token de primeiro acesso para usuário.
        """

        """
        Obtém o token como string e cria link.
        """
        refresh = RefreshToken.for_user(user)
        token_expiration = refresh.access_token.set_exp(lifetime=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"])
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        token_expiration = refresh.access_token.get('exp', None)
        link = f"http://localhost:3000/first-access/?access_token={access_token}&refresh_token={refresh_token}"

        """
        Calcula tempo restante de expiração do token
        """
        current_time = int(time.time())
        time_until_expiration = token_expiration - current_time

        """
        Renderiza o HTML do e-mail usando um template.
        """
        context = {
            "link": link,
            "user": user.first_name,
            "token_expiration": int(time_until_expiration / 60 / 60)
        }
        html_message = render_to_string('first_access/email.html', context)
        text_message = strip_tags(html_message)

        """
        Envia o e-mail.
        """
        subject = "Primeiro acesso à plataforma ARGOS."
        from_email = settings.EMAIL_HOST_USER
        recipient_list = [email]
        msg = EmailMultiAlternatives(subject, text_message, from_email, recipient_list)
        msg.attach_alternative(html_message, "text/html")
        msg.send()

    def post(self, request):
        """
        Realiza Create.
        """

        """
        Verifica se nome do grupo existe e não é null. 
        """
        try:
            group_name = request.data.get("group_name")  
            type = request.data.get("type")  
            email = request.data.get("email")  
            if not email or not group_name or type != "normal" and type != "super":
                return Response({"info": "Erro ao setar valores dos campos.", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({"info": "Erro ao setar valores dos campos.", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

        """
        Restaura usuário caso já exista.        
        """
        user = CustomUser.objects.deleted().filter(email=email).first()
        if user and user.is_deleted:

            """
            Adiciona usuário ao grupo.
            """
            if type == "super":
                """
                Cria grupo se não existir e insere usuário.
                """
                group, created = Group.objects.get_or_create(name=group_name)  
                group.user_set.add(user)
            else:
                """
                Verifica se grupo já possui administrador.
                """ 
                try:
                    group = Group.objects.get(name=group_name)
                    group.user_set.add(user)
                except:
                    return Response({"info": "Erro pois grupo não possui administrador.", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

            """
            Salva dados do usuário.
            """
            user.is_deleted = False
            user.save()

            """
            Envia e-mail de primeiro acesso.        
            """
            self.send_first_login_email(email, user)

            return Response({"info": "E-mail já existe. Usuário restaurado com sucesso.", "status": status.HTTP_201_CREATED}, status=status.HTTP_201_CREATED)
            
        """
        Verifica dados de entrada.        
        """
        serializer = CustomUserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = CustomUser.objects.filter(email=email).first()
            if type == "super":
                """
                Salva usuário.
                """
                user = serializer.save(is_staff=True, is_superuser=False)

                """
                Cria grupo se não existir e insere usuário.
                """
                group, created = Group.objects.get_or_create(name=group_name)  
                group.user_set.add(user)
                
            else:
                """
                Verifica se grupo já possui administrador.
                """ 
                try:
                    group = Group.objects.get(name=group_name)
                except:
                    return Response({"info": "Erro pois grupo não possui administrador.", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
                    
                user = serializer.save(is_staff=False, is_superuser=False)
                group.user_set.add(user)
            
            """
            Envia e-mail de primeiro acesso.        
            """
            self.send_first_login_email(email, user)    

            return Response({"info": "Sucesso ao criar usuário e e-mail enviado com sucesso.", "status": status.HTTP_201_CREATED}, status=status.HTTP_201_CREATED)
        
        else:
            return Response({"info": "Erro ao criar usuário.", "errors": serializer.errors, "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request, uuid=None):
        """
        Realiza Read.
        """
        if uuid:
            user = CustomUser.objects.filter(uuid=uuid).first()
            if user:
                serializer = CustomUserSerializer(user)
                user_groups = user.groups.all()
                group_names = [group.name for group in user_groups]
                return Response({"info": "Sucesso ao ler usuário.", "data": serializer.data, "user_groups": group_names}, status=status.HTTP_200_OK)
            return Response({"info": "Erro ao encontrar usuário.", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"info": "Erro ao encontrar usuário.", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

    ##### TESTE #####
    # def automatic_login(self, request, email, password):
    #     from django.contrib.auth import login
    #     user = authenticate(request, username=email, password=password)
    #     if user is not None:
    #         login(request, user)
    #         return user
    #     return None
    ###############

    def patch(self, request, uuid=None):
        """
        Realiza Update.
        """

        ##### TESTE #####
        # self.automatic_login(request, 'admin@email.com', 'admin')
        # print('\n----------------------\n', request.user, '\n----------------------\n')
        #################

        """
        Verifica se nome do grupo existe e não é null. 
        """
        try:
            type = request.data.get("type")  
            if type != "normal" and type != "super":
                return Response({"info": "Erro ao setar valores dos campos.", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({"info": "Erro ao setar valores dos campos.", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        
        """
        Verifica se usuário a ser atualizado existe.
        """
        user = CustomUser.objects.filter(uuid=uuid).first()
        if not user:
            return Response({"info": "Erro ao encontrar usuário.", "status": status.HTTP_404_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)

        """
        Verifica dados de entrada.
        """
        serializer = CustomUserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            """
            Se o usuário logado pelo token for admin, permite fazer alterações.
            """

            if request.user.is_staff:
                
                old_group_name = request.data.get("old_group_name")
                new_group_name = request.data.get("new_group_name")

                """
                Verifica se variáveis foram setadas corretamente.
                """
                if not new_group_name or not old_group_name:
                    return Response({"info": "Erro nos nomes de grupos, pois não podem ser vazio.", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
                
                """
                Atualiza permissões.
                """
                if type == "super":
                    val=True
                else:
                    """
                    Verificar se usuário é o único admin para grupo não ficar sem administrador.
                    """

                    try:
                        group = Group.objects.get(name=old_group_name)
                        count_admin = group.user_set.filter(is_staff=True).count()  
                    except:
                        return Response({"info": "Erro pois grupo não existe.", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
            
                    if count_admin == 1:
                        return Response({"info": "Erro ao modificar permissão, grupos devem possuir ao menos um administrador.", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
                    
                    val=False

                """
                Verifica se usuário está contido em algum grupo, se sim altera o nome desse grupo pelo nome do novo grupo.
                """
                if old_group_name in user.groups.values_list('name', flat=True):        
                    old_group = Group.objects.get(name=old_group_name)
                    old_group.name = new_group_name
                    old_group.save()
                else:
                    return Response({"info": "Erro ao encontrar grupo correspondente ao nome fornecido.", "errors": serializer.errors, "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
            
                serializer.save(is_staff=val)
                return Response({"info": "Sucesso ao atualizar usuário.", "status": status.HTTP_200_OK}, status=status.HTTP_200_OK)
            else:
                return Response({"info": "Usuário não possui permissão para modificação.", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"info": "Erro ao atualizar usuário.", "errors": serializer.errors, "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, uuid=None):
        """
        Realiza Delete. 
        """
        user = CustomUser.objects.filter(uuid=uuid).first()
        if not user:
            return Response({"info": "Erro ao encontrar usuário.", "status": status.HTTP_404_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
        
        if not user.is_staff:

            """
            Remove o usuário de todos os grupos.
            """
            user.groups.clear()
            user.delete()

            return Response({"info": "Sucesso ao exluir usuário.", "status": status.HTTP_204_NO_CONTENT}, status=status.HTTP_204_NO_CONTENT)
            
        """
        Percorre todos os grupos que o usuário pertence, verifica se é o unico admin, senão for exlui somente ele mesmo, se for exclui todo o grupo.
        """  
        info = []
        group_names = user.groups.values_list('name', flat=True)
        for group_name in group_names:
            group = Group.objects.get(name=group_name)
            count_admin = group.user_set.filter(is_staff=True).count()

            if count_admin == 1:
                group.user_set.all().delete()
                group.delete()
                info.append(f"Sucesso ao excluir grupo {group_name}.")
            else:
                """
                Remove o usuário apenas deste grupo.
                """
                group.user_set.remove(user)
                info.append(f"Sucesso ao exluir usuário do grupo {group_name}.")

        """
        Varrer e deletar todos os grupos que estiverem vazios (sem nenhum usuário).
        """
        # for group in Group.objects.all():
        #     if not group.user_set.exists():
        #         group.delete()
        #         # info.append(f"Grupo vazio {group.name} foi excluído.")

        return Response({"info": info, "status": status.HTTP_204_NO_CONTENT}, status=status.HTTP_204_NO_CONTENT)


class GetGroupView(APIView):
    pass

class GetAllGroupsView(APIView):
    pass
        
class LoginView(APIView):
    """
    Autenticação de usuário, posteriormente o retorno de um token ou mensagem de erro.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            email = request.data.get("email")
            password = request.data.get("password")
        except:
            return Response({"info": "Alguma variável não foi setada corretamente.", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        
        """
        Verifica se o email e a senha foram fornecidos na requisição.
        """
        if not email or not password:
            return Response({"info": "Informe email e senha válidos.", "status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

        """
        Autentica o usuário usando o email e a senha.
        """
        user = authenticate(username=email, password=password)

        """
        Verifica se a autenticação foi bem-sucedida.
        """
        if user is not None:
            """
            Gera os tokens JWT e retorna resposta.
            """
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            user_groups = user.groups.all()
            # group_names = [group.name for group in user_groups]
            group_names = []
            for group in user_groups:
                # if group.name != "NOME ORIGINAL DO GRUPO":
                    group_names.append(group.name)

            serializer = CustomUserSerializer(user)
            return Response({"access_token": access_token, "refresh_token": refresh_token, "data": serializer.data, "groups": group_names,"status": status.HTTP_200_OK}, status=status.HTTP_200_OK)
        else:
            return Response({"info": "Email ou senha incorretos.", "status": status.HTTP_401_UNAUTHORIZED}, status=status.HTTP_401_UNAUTHORIZED)

class UpdateAccessView(APIView):
    pass
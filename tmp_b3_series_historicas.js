ï»¿//*****************************************************************************
//Objetivo:					Encapsular funcionalidades da SÃ©rie Historica de CotaÃ§Ãµes
//Autor:					Camila D. Silva
//Data:						12/11/2005
//Modificado por:			
//Data Ultima alteraÃ§Ã£o:	
//Motivo:					

//*****************************************************************************

//*****************************************************************************
// DECLARAÃÃO DAS VARIÃVEIS
//*****************************************************************************

/******************************************************************************************
/ Objetivo  : Define propriedade e valor da mesma de acordo com os valores passados pelo usuÃ¡rio
/ Premissas : 
/ Entradas  : objObjeto - ReferÃªncia ao objeto que terÃ¡ o valor da propriedade especificada alterada
/ 			: strId - Id do objeto
/ 			: strPropriedade - Propriedade a ser alterada
/ 			: strValorPropriedade - Valor a ser atribuido a propriedade
/ Retorno   : Nenhum
/******************************************************************************************/
function DefineValorPropriedade(objObjeto, strId, strPropriedade, strValorPropriedade)
{
	var intCont = new Number(0); // VariÃ¡vel utilizada no laÃ§o for

	for (intCont = 0; intCont < objObjeto.length; intCont++)
	{
		if (objObjeto[intCont].id.indexOf(strId) != -1)
		{
			eval('objObjeto[' + intCont + '].' + strPropriedade + '=' + strValorPropriedade);
			break;
		}
	}
}
/******************************************************************************************
/ Objetivo  : Verifica qual opÃ§Ã£o foi selecionada
/ Premissas : 
/ Entradas  : intOpcao - ReferÃªncia ao objeto que terÃ¡ o valor da propriedade especificada alterada
/ Retorno   : Nenhum
/******************************************************************************************/
function VerificaOpcao(intOpcao)
{
	if (intOpcao == 1)
	{
		DefineValorPropriedade(document.frmEnviar, 'chkAnual', 'disabled', true);
		DefineValorPropriedade(document.frmEnviar, 'chkAnual', 'checked', false);			
		DefineValorPropriedade(document.frmEnviar, 'cboAnual', 'disabled', true);			
		DefineValorPropriedade(document.frmEnviar, 'cboAnual', 'selectedIndex', '0');						
		DefineValorPropriedade(document.frmEnviar, 'chkMensal', 'disabled', true);		
		DefineValorPropriedade(document.frmEnviar, 'chkMensal', 'checked', false);					
		DefineValorPropriedade(document.frmEnviar, 'txtMensal', 'disabled', true);					
		DefineValorPropriedade(document.frmEnviar, 'txtMensal', 'value', '\'\'');								
		DefineValorPropriedade(document.frmEnviar, 'chkDiario', 'disabled', true);		
		DefineValorPropriedade(document.frmEnviar, 'chkDiario', 'checked', false);		
		DefineValorPropriedade(document.frmEnviar, 'txtDiario', 'disabled', true);				
		DefineValorPropriedade(document.frmEnviar, 'txtDiario', 'value', '\'\'');						
	}
	else
	{
		DefineValorPropriedade(document.frmEnviar, 'chkAnual', 'disabled', false);
		DefineValorPropriedade(document.frmEnviar, 'chkAnual', 'checked', false);			
		DefineValorPropriedade(document.frmEnviar, 'cboAnual', 'disabled', true);			
		DefineValorPropriedade(document.frmEnviar, 'cboAnual', 'selectedIndex', '0');						
		DefineValorPropriedade(document.frmEnviar, 'chkMensal', 'disabled', false);		
		DefineValorPropriedade(document.frmEnviar, 'chkMensal', 'checked', false);			
		DefineValorPropriedade(document.frmEnviar, 'txtMensal', 'disabled', true);					
		DefineValorPropriedade(document.frmEnviar, 'txtMensal', 'value', '\'\'');								
		DefineValorPropriedade(document.frmEnviar, 'chkDiario', 'disabled', false);		
		DefineValorPropriedade(document.frmEnviar, 'chkDiario', 'checked', false);		
		DefineValorPropriedade(document.frmEnviar, 'txtDiario', 'disabled', true);				
		DefineValorPropriedade(document.frmEnviar, 'txtDiario', 'value', '\'\'');						
	}
}
//*****************************************************************************
//Objetivo:					Chama a funÃ§Ã£o que que valida dados 
//Entradas:					-
//SaÃ­da:					Nenhuma
//*****************************************************************************	
	function ExecutaValidaFormSeriesHistoricas(objForm)
	{
	Validacao(objForm);
	}
	
/******************************************************************************
/ Objetivo  : Cancela o evento caso nÃ£o seja nÃºmero
/ Premissas : Nenhuma
/ Entradas  : Nenhuma
/ Retorno   : Nenhum
/******************************************************************************/
function CampoNumerico()
{
	var intEvento; // Evento
	intEvento = event.keyCode;
	if ((intEvento < 48) || (intEvento > 57))
	{
		event.cancelBubble = true
		event.returnValue = false;
	}
}

//*****************************************************************************
//Objetivo:					Validar os dados do formulÃ¡rio
//Entradas:					-
//SaÃ­da:					Nenhuma
//*****************************************************************************		
function Validacao(objForm)
{
	var strEmail = objForm.txtEmail.value // Recebe o valor do Email
	
	if (objForm.txtNome.value == "")
	{
		alert("Por Favor preencha o campo Nome.");
		objForm.txtNome.focus();
		return(false);
	}
	/*if (objForm.txtInstituicao.value == "")
	{
		alert("Por Favor preencha o campo InstituiÃ§Ã£o.");
		objForm.txtInstituicao.focus();
		return(false);
	}*/
	if (objForm.txtTelDDD.value == "")
	{
		alert("Por Favor preencha o campo DDD-Telefone.");
		objForm.txtTelDDD.focus();
		return(false);
	}
	if (objForm.txtTelefone.value == "")
	{
		alert("Por Favor preencha o campo Telefone.");
		objForm.txtTelefone.focus();
		return(false);
	}
	if ((objForm.txtEmail.value == "")){
		alert("Por Favor preencha o campo e-mail.");
		objForm.txtEmail.focus();
		return false;								
	}
	if (!ValidarEmail(objForm.txtEmail.value)){
		alert("E-mail invÃ¡lido.");
		objForm.txtEmail.focus();
		return false;								
	}
	if (objForm.txtEndereco.value == "")
	{
		alert("Por Favor preencha o campo EndereÃ§o.");
		objForm.txtEndereco.focus();
		return(false);
	}
	if (objForm.txtCidade.value == "")
	{
		alert("Por Favor preencha o campo Cidade.");
		objForm.txtCidade.focus();
		return(false);
	}
	if (objForm.txtEstado.value == "")
	{
		alert("Por Favor preencha o campo Estado.");
		objForm.txtEstado.focus();
		return(false);
	}
	if (objForm.txtCep.value == "")
	{
		alert("Por Favor preencha o campo CEP.");
		objForm.txtCep.focus();
		return(false);
	}
	/*if( (objForm.chkCompleto.checked == false) && (objForm.chkAnual.checked == false) && (objForm.chkMensal.checked == false) && (objForm.chkDiario.checked == false))
	{
		alert("Por Favor escolha uma das opÃ§Ãµes de Banco de Dados.");
		return(false);
	}*/
	if ((objForm.rdPeriodo[0].checked == false) && (objForm.rdPeriodo[1].checked == false)){
		alert("Por favor escolha Banco de Dados completo ou Informe o perÃ­odo desejado.");
		objForm.rdPeriodo[0].focus();
		return false;
	}
	if ((objForm.rdPeriodo[1].checked == true) && (objForm.txtPeriodo == "")){
		alert("Por favor preencha o perÃ­odo desejado.");
		objForm.txtPeriodo.focus();
		return false;
	}
	
	objForm.submit();
}

//*****************************************************************************
//Objetivo:					Abrir o popup do FormulÃ¡rio
//Entradas:					-
//SaÃ­da:					Nenhuma
//*****************************************************************************		
function AbreFormularioSeriesHistoricas() 
{
	var intH;	 //VariÃ¡vel auxiliar para posicionamento do topo
	var intW; 	//VariÃ¡vel auxiliar para posicionamento da Esquerda
	
	intH = (screen.height - 600) / 2;
	intW = (screen.width - 800) / 2;
			
	window.open('/pt-br/cotacoes-historicas/FormConsultaSeriesHistoricas.asp','','width=800,height=600,scrollbars=yes,top=' + intH + ',left=' + intW);
}	


//*****************************************************************************
//Objetivo:					Chama a funÃ§Ã£o que que valida dados 
//Entradas:					-
//SaÃ­da:					Nenhuma
//*****************************************************************************	
function ExecutaValidaFormSeriesHistoricasI(objForm)
{
	ValidacaoI(objForm);
}

//*****************************************************************************
//Objetivo:					Validar os dados do formulÃ¡rio
//Entradas:					-
//SaÃ­da:					Nenhuma
//*****************************************************************************		
function ValidacaoI(objForm)
{
	var strEmail = objForm.txtEmail.value // Recebe o valor do Email
		
	if (objForm.txtName.value == "")
	{
		alert("Por Favor preencha o campo Nome.");
		objForm.txtName.focus();
		return(false);
	}
	if (objForm.txtCompany.value == "")
	{
		alert("Por Favor preencha o campo InstituiÃ§Ã£o.");
		objForm.txtCompany.focus();
		return(false);
	}
	if (objForm.txtPhoneNumber.value == "")
	{
		alert("Por Favor preencha o campo DDD-Telefone.");
		objForm.txtPhoneNumber.focus();
		return(false);
	}
	if ((objForm.txtEmail.value == "")){
		alert("Por Favor preencha o campo e-mail.");
		objForm.txtEmail.focus();
		return false;								
	}
	if (!ValidarEmail(objForm.txtEmail.value)){
		alert("E-mail invÃ¡lido.");
		objForm.txtEmail.focus();
		return false;								
	}
	if (objForm.txtAdress.value == "")
	{
		alert("Por Favor preencha o campo EndereÃ§o.");
		objForm.txtAdress.focus();
		return(false);
	}
	if (objForm.txtCity.value == "")
	{
		alert("Por Favor preencha o campo Cidade.");
		objForm.txtCity.focus();
		return(false);
	}
	if (objForm.txtState.value == "")
	{
		alert("Por Favor preencha o campo Estado.");
		objForm.txtState.focus();
		return(false);
	}
	if (objForm.txtCountry.value == "")
	{
		alert("Por Favor preencha o campo Country.");
		objForm.txtCountry.focus();
		return(false);
	}
	if (objForm.txtZipCode.value == "")
	{
		alert("Por Favor preencha o campo CEP.");
		objForm.txtZipCode.focus();
		return(false);
	}
	if( (objForm.chkComplete.checked == false) && (objForm.chkYearly.checked == false) && (objForm.chkMonthly.checked == false) && (objForm.chkDaily.checked == false))
	{
		alert("Por Favor escolha uma das opÃ§Ãµes de Banco de Dados.");
		return(false);
	}		
	
	objForm.submit();
}
//============================================================================================
// Objetivo........: Valida FormulÃ¡rio
// Premissas.......:
// Entradas........: objFrm objeto form
// Retorno.........: 
//============================================================================================	
function ValidaAcesso(objFrm)
{
	var strEmail;	//Email do usuÃ¡rio
	
	if (objFrm.txtEmail.value == "") {
		alert("Por favor, preencha o campo e-mail.")
		objFrm.txtEmail.focus();
		return(false);
	}
	strEmail = objFrm.txtEmail.value // Recebe o valor do Email
	if(!(ValidarEmail(strEmail)))
	{
		objFrm.txtEmail.focus();
		alert("E-mail invÃ¡lido.");
		return(false);
	}
	if (objFrm.pwdSenha.value == "") {
		alert("Por favor, informe a senha.")
		objFrm.pwdSenha.focus();
		return(false);
	}
	objFrm.submit();
}

//============================================================================================
// Objetivo........: Faz download do arquivo solicitado
// Premissas.......:
// Entradas........: obj
// Retorno.........: 
//============================================================================================	
function AbrirArquivo(strNomeArq){
	var strArq;		//Abre arquivo para download
	
	strArq = '/InstDados/SerHist/' + strNomeArq;
	/*dcsMultiTrack('DCS.dcsuri', strArq,'WT.ti','Relatorio-'+strNomeArq+'');*/
	window.open (strArq, '_blank');
}

//============================================================================================
// objErrotivo........: FunÃ§Ã£o que vÃ¡lida dados do usuÃ¡rio
// Premissas.......:
// Entradas........: objFrm - formulÃ¡rio
// Retorno.........:
//============================================================================================
function ValidaDadosUsuario (objFrm){
	try{
		if (objFrm.txtNome.value == ""){
			objFrm.txtNome.focus();
			throw "O campo Nome Ã© obrigatÃ³rio."
		}
		/*if (objFrm.txtInstituicao.value == ""){
			objFrm.txtInstituicao.focus();
			throw "O campo InstituiÃ§Ã£o Ã© obrigatÃ³rio."
		}*/
		if (objFrm.txtCPF.value == ""){
			objFrm.txtCPF.focus();
			throw "O campo CPF/CNPJ Ã© obrigatÃ³rio."
		}
		if (objFrm.txtCPF.value.length == 11 || objFrm.txtCPF.value.length == 14){
			if (objFrm.txtCPF.value.length == 11){
				if(ValidaCPF(objFrm.txtCPF.value)==false)
				{
					if(isNaN(objFrm.txtCPF.value)==true)
					{
						throw "O CPF deve ser digitado sem pontos ou barras, somente nÃºmeros."
					}
					else
					{
						throw "CPF InvÃ¡lido."
					}
				}
			}
			else{
				if(ValidaCNPJ(objFrm.txtCPF.value)==false)
				{
					if(isNaN(objFrm.txtCPF.value)==true)
					{
						throw "O CNPJ dever ser digitado sem pontos ou barras, somente nÃºmeros"
					}
					else
					{
						throw "CNPJ InvÃ¡lido"
					}
				}
			}
		}
		else{
			objFrm.txtCPF.focus();
			throw "O campo CPF/CNPJ Ã© invÃ¡lido."
		}
		//Utiliza a funÃ§Ã£o de valida email e verifica o seu retorno
		if(!(ValidarEmail(objFrm.txtEmail.value)))
		{
			objFrm.txtEmail.focus();
			throw ("E-mail invÃ¡lido");
		}
		if (objFrm.Acao.value == "Alterar"){
			objFrm.action = "ExecutaAcaoUsuario.asp?Acao=Alterar"
			objFrm.submit();
		}
		else{
		    if (objFrm.pwdSenha.value == ""){
		        objFrm.pwdSenha.focus();
		        throw "O campo Senha Ã© obrigatÃ³rio."
	        }
	        if (objFrm.pwdSenha.value.length < 3){
		        objFrm.pwdSenha.focus();
		        throw "O campo Senha deve conter no mÃ­nimo 3 caracteres."
	        }
	        if (objFrm.pwdConfirmarSenha.value == ""){
		        objFrm.pwdConfirmarSenha.focus();
		        throw "O campo Confirmar Senha Ã© obrigatÃ³rio."
	        }
	        if (objFrm.pwdSenha.value != objFrm.pwdConfirmarSenha.value){
		        objFrm.pwdConfirmarSenha.focus();
		        throw "O campo Senha deve ser igual ao Confirmar Senha."
	        }
			objFrm.action = "FormTermoResponsa.asp"
			objFrm.submit();
		}
	}
	catch(objException)
	{
		if(!(isNaN(objException.number)))
		{
			alert(objException.message);
		}
		else
		{
			alert(objException.toString());
		}
	}
}

//============================================================================================
// Objetivo........: Monta combo com os dia escolhidos
// Premissas.......:
// Entradas........: mes - mÃªs selecionado
// Retorno.........: 
//============================================================================================	
function MontaComboDia(mes){
	

	var strDados;  //Dados 
	var arrDados;  //Array com os dados
	var intCont;   //Contador
	var intCont1;  //Contador
	var intCont2;  //Contador
	
	strDados = document.getElementById("hdnDados").value;
	arrDados = strDados.split("_|_");
	intCont1 = 1;
	
	for (var intCont2=0; intCont2 < 31; intCont2++) {  
		document.getElementById("cboDia").options[intCont1] = null;
	}

	for (var intCont=0; intCont < arrDados.length; intCont++) {   
		var strM =  arrDados[intCont].slice(0,2);  
		if (mes == strM){
			document.getElementById("cboDia").options[intCont1] = new Option(arrDados[intCont].slice(3,5),arrDados[intCont].slice(6,28));
			intCont1 = intCont1 + 1;
		}
	}
}

//============================================================================================
// Objetivo........: FunÃ§Ã£o que vÃ¡lida dados do usuÃ¡rio (atualizaÃ§Ã£o)
// Premissas.......:
// Entradas........: objFrm - formulÃ¡rio
// Retorno.........:
//============================================================================================
function ValidaAtualizaUsua (objFrm){
	try{
		
		/*if (objFrm.txtInstituicao.value == ""){
			objFrm.txtInstituicao.focus();
			throw "O campo InstituiÃ§Ã£o Ã© obrigatÃ³rio."
		}*/
		if (objFrm.txtCPF.value == ""){
			objFrm.txtCPF.focus();
			throw "O campo CPF/CNPJ Ã© obrigatÃ³rio."
		}
		if (objFrm.txtCPF.value.length == 11 || objFrm.txtCPF.value.length == 14){
			if (objFrm.txtCPF.value.length == 11){
				if(ValidaCPF(objFrm.txtCPF.value)==false)
				{
					if(isNaN(objFrm.txtCPF.value)==true)
					{
						throw "O CPF deve ser digitado sem pontos ou barras, somente nÃºmeros."
					}
					else
					{
						throw "CPF InvÃ¡lido."
					}
				}
			}
			else{
				if(ValidaCNPJ(objFrm.txtCPF.value)==false)
				{
					if(isNaN(objFrm.txtCPF.value)==true)
					{
						throw "O CNPJ dever ser digitado sem pontos ou barras, somente nÃºmeros"
					}
					else
					{
						throw "CNPJ InvÃ¡lido"
					}
				}
			}
		}
		else{
			objFrm.txtCPF.focus();
			throw "O campo CPF/CNPJ Ã© invÃ¡lido."
		}
		objFrm.submit();
	}
	catch(objException)
	{
		if(!(isNaN(objException.number)))
		{
			alert(objException.message);
		}
		else
		{
			alert(objException.toString());
		}
	}
}

//============================================================================================
// Objetivo........: FunÃ§Ã£o que vÃ¡lida dados do usuÃ¡rio (atualizaÃ§Ã£o)
// Premissas.......:
// Entradas........: objFrm - formulÃ¡rio
// Retorno.........:
//============================================================================================
function ExecutaValidaRecupSenha(objFrm){
	try{
		//Utiliza a funÃ§Ã£o de valida email e verifica o seu retorno
		if(!ValidarEmail(objFrm.txtEmail.value))
		{
			objFrm.txtEmail.focus();
			throw ("E-mail invÃ¡lido.");
		}
		objFrm.submit();
	}
	catch(objException)
	{
		if(!(isNaN(objException.number)))
		{
			alert(objException.message);
		}
		else
		{
			alert(objException.toString());
		}
	}
}
//============================================================================================
// Objetivo........: FunÃ§Ã£o que vÃ¡lida a confirmaÃ§Ã£o da senha
// Premissas.......:
// Entradas........: objFrm - formulÃ¡rio
// Retorno.........:
//============================================================================================
function ValidaConfirmaSenha (objFrm){
	try{
		
		if (objFrm.pwdSenha.value == ""){
			objFrm.pwdSenha.focus();
			throw "Confirme sua senha."
		}
		objFrm.submit();
	}
	catch(objException)
	{
		if(!(isNaN(objException.number)))
		{
			alert(objException.message);
		}
		else
		{
			alert(objException.toString());
		}
	}
}
//============================================================================================
// Objetivo........: Faz download do arquivo solicitado
// Premissas.......:
// Entradas........: obj
// Retorno.........: 
//============================================================================================	
function AbrirValidacao(strNomeArq){
	var strPagina;  // PÃ¡gina que faz download do arquivo
	var intH;		//VariÃ¡vel auxiliar para posicionamento do topo
	var intW;		//VariÃ¡vel auxiliar para posicionamento da Esquerda
	if (strNomeArq != ''){
		intH = (screen.height - 600) / 2;	
		intW = (screen.width - 800) / 2;	
		strPagina = 'FormConsultaValida.asp?arq=' +strNomeArq+ '';
		window.open(strPagina,'','width=340,height=245,scrollbars=no,top=' + intH + ',left=' + intW);
	}
}

//============================================================================================
// Objetivo........: FunÃ§Ã£o que vÃ¡lida se usuÃ¡rio informou o texto da imagem
// Premissas.......:
// Entradas........: objFrm - formulÃ¡rio
// Retorno.........:
//============================================================================================
function ValidaTxtImg(objFrm){
	try{
		if (objFrm.txtTexto.value == ""){
			objFrm.txtTexto.focus();
			throw "Informe a sequÃªncia de caracteres da imagem."
		}
		objFrm.action='FormConsultaValidaImagem.asp';
		objFrm.submit();
	}
	catch(objException)
	{
		if(!(isNaN(objException.number)))
		{
			alert(objException.message);
		}
		else
		{
			alert(objException.toString());
		}
	}
}
//============================================================================================
// objetivo........: Verifica se numero do CNPJ Ã© valido
// Premissas.......:
// Entradas........: nenhuma
// Retorno.........: true - numero valido / false - numero invalido
//============================================================================================
function ValidaCNPJ(intCNPJ)
{
   var intCNPJLocal ;		//Numero do CNPJ
   var intRespostaLocal ;	//Resposta Local
   var intDigito1 ;			//Digito Verificador 1
   var intDigito2 ;			//Digito Verificador 2
   var intCont ;			//Contador
   var intSoma ;			//Soma
 
   intCNPJLocal = intCNPJ ;
 
  if ((intCNPJLocal.length < 14) || (intCNPJLocal == "00000000000000"))
  {
    intRespostaLocal = false ;
  }
  else
  {
	intRespostaLocal = true ;
  }
 
  if (intRespostaLocal == true)
  {
		intSoma = 0 ;
 
		for (intCont = 1; intCont <= 12; intCont++) 
		{
			if (intCont < 5)
			{
				intSoma = intSoma + (intCNPJLocal.substring(intCont-1,intCont) * (6-intCont))
			}
			else
			{
				intSoma = intSoma + (intCNPJLocal.substring(intCont-1,intCont) * (14-intCont))
			}
		}
 
		intDigito1 = 11 - (intSoma % 11) ;
		if (intDigito1 > 9)
		{
			intDigito1 = 0 ;
		}
 
		intSoma = 0 ;
   
		for (intCont = 1; intCont <= 13; intCont++)
		{
			if (intCont < 6)
		    {
				intSoma = intSoma + (intCNPJLocal.substring(intCont-1,intCont) * (7-intCont)) ;
		    }
		    else
		    {
				intSoma = intSoma + (intCNPJLocal.substring(intCont-1,intCont) * (15-intCont)) ;
		    }
		}
 
		intDigito2 = 11 - (intSoma % 11) ;
		if (intDigito2 > 9)
		{
			intDigito2 = 0 ;
		}
 
		if ((intDigito1 == intCNPJLocal.substr(12,1)) && (intDigito2 == intCNPJLocal.substr(13,1)))
		{
			intRespostaLocal = true
		}
		else 
		{
		    intRespostaLocal = false
		}
 
  }
    return intRespostaLocal
}

/******************************************************************************
/ Objetivo  : Validar se o CPF Ã© vÃ¡lido
/ Premissas : Nenhuma
/ Entradas  : CPF UsuÃ¡rio
/ Retorno   : Nenhum
/******************************************************************************/
function ValidaCPF(CPF)
{
	var strCharCPF = false;				//Caracter do CPF
	var strFirstChr = CPF.charAt(0);	//Primeiro caracter
	for ( var i=0; i<=10; i++ )
	{
		var c = CPF.charAt(i);
		if( ! ((c>="0")&&(c<="9")) ) 
		{	
			return false;
		}
		if( c!=strFirstChr ) 
			strCharCPF = true;
	}
	if( ! strCharCPF ) {
		return false;
	}
	soma=0;
	for ( i=0; i<9; i++ ) { 
		soma += (10-i) * ( eval(CPF.charAt(i)) ); 
	}
	digito_verificador = 11-(soma % 11);
	if ( (soma % 11) < 2 ) 
		digito_verificador = 0;
	if ( eval(CPF.charAt(9)) != digito_verificador ) { 
		return false; 
	}
	soma=0; 
	for ( i=0; i<9; i++ ) { 
		soma += (11-i) * ( eval(CPF.charAt(i)) ); 
	} 
	soma += 2 * ( eval(CPF.charAt(9)) ); 
	digito_verificador = 11-(soma % 11); 
	if ( (soma % 11) < 2 ) 
		digito_verificador = 0; 
	if ( eval(CPF.charAt(10)) != digito_verificador ) { 
		return false; 
	}
	return true; 
}	

/******************************************************************************
/ Objetivo  : Voltar a posiÃ§Ã£o inicial do combo
/ Premissas : Nenhuma
/ Entradas  : CPF UsuÃ¡rio
/ Retorno   : Nenhum
/******************************************************************************/
function VoltarPosInic(strTipo){
	if (strTipo == 1) {
		document.frmSerHist.cboAno.selectedIndex = 0;	
	}
	if (strTipo == 2) {
		document.frmSerHist.cboMes.selectedIndex = 0;	
	}
	if (strTipo == 3) {
		document.frmSerHist.cboMesDia.selectedIndex = 0;	
		document.frmSerHist.cboDia.selectedIndex = 0;	
	}
}

// ----------------------------------------------------------------------------
// Objetivo  : Validar Email
// Premissas : Nenhuma
// Entradas  : strEmail - Email recebido para validaÃ§Ã£o
// Retorno   : true ou false
// ----------------------------------------------------------------------------
function ValidarEmail(strEmail)
{
	try
    {
		//var strPadrao = /^([\w-]+(?:\.[\w-]+)*)@((?:[\w-]+\.)*\w[\w-]{0,66})\.([a-z]{2,6}(?:\.[a-z]{2})?)$/i; // Regra da expressÃ£o regular
		var strPadrao = /^([\&\w-\.]+)@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.)|(([\w-]+\.)+))([a-zA-Z]{2,4}|[0-9]{1,3})(\]?)$/i;
		var objReg = new RegExp(strPadrao); // Objeto ExpressÃ£o Regular
		var blnCondicao // Variavel auxiliar true or false
	    
		objReg.exec(strPadrao)
		objReg.global == true;
		if (!(objReg.test(strEmail)))
		{   
			throw "Email InvÃ¡lido";
		}
		blnCondicao = true;
	}
	catch(objEx)
	{
		blnCondicao = false;
	}
	finally
	{
		return blnCondicao
	}
}

//============================================================================================
// objErrotivo........: FunÃ§Ã£o que vÃ¡lida dados do usuÃ¡rio
// Premissas.......:
// Entradas........: objFrm - formulÃ¡rio, strTipo - tipo de validaÃ§Ã£o
// Retorno.........:
//============================================================================================
function ValidaSenhaUsuario (objFrm, strTipo){
	try{
	     if (objFrm.pwdSenhaAtual.value == ""){
		    objFrm.pwdSenhaAtual.focus();
		    throw "O campo Senha Atual Ã© obrigatÃ³rio."
        }
        if (objFrm.pwdSenha.value == ""){
		    objFrm.pwdSenha.focus();
		    throw "O campo Senha Nova Ã© obrigatÃ³rio."
        }
        if (objFrm.pwdSenha.value.length < 3){
            objFrm.pwdSenha.value = "";
            objFrm.pwdConfirmarSenha.value = "";
            objFrm.pwdSenha.focus();
            throw "A sua senha deve ter entre 3 e 15 caracteres."
        }
        if (objFrm.pwdConfirmarSenha.value == ""){
            objFrm.pwdConfirmarSenha.focus();
            throw "O campo Confirmar Senha Ã© obrigatÃ³rio."
        }
        if (objFrm.pwdSenha.value != objFrm.pwdConfirmarSenha.value){
            objFrm.pwdConfirmarSenha.focus();
            throw "O campo Senha deve ser igual ao Confirmar Senha."
        }
        if (objFrm.pwdSenhaAtual.value == objFrm.pwdSenha.value){
            objFrm.pwdSenhaAtual.value = "";
            objFrm.pwdSenha.value = "";
            objFrm.pwdConfirmarSenha.value = "";
		    objFrm.pwdSenhaAtual.focus();
		    throw "A nova senha deve ser diferente da anterior."
        }
        objFrm.submit();
	}
	catch(objException)
	{
		if(!(isNaN(objException.number)))
		{
			alert(objException.message);
		}
		else
		{
			alert(objException.toString());
		}
	}
}

//============================================================================================
// objetivo........: Limpa o campo perÃ­odo no caso de Banco de Dados completo / habilita campo perÃ­odo
// Premissas.......: nenhuma
// Entradas........: nehuma
// Retorno.........: nenhum
//============================================================================================
function VerificaCampoPeriodo(){
    if (document.frmEnviar.rdPeriodo[0].checked == true) {
        document.frmEnviar.txtPeriodo.value = "";
        document.frmEnviar.txtPeriodo.disabled = true;
    }
    if (document.frmEnviar.rdPeriodo[1].checked == true) {
        document.frmEnviar.txtPeriodo.disabled = false;
    }
}

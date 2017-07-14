# -*- coding: utf-8 -*-
import json
import logging
import sys

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, StreamingHttpResponse, Http404

from data_import.SteelPricePredict.data_cleaning import get_history_price,create_single_model
from data_import.SteelPricePredict.pre_config import steel_type,predict_method,time_scale,INFO,WARNING,model_classname
import data_import.SteelPricePredict.PredictModels as PredictModels
from . import util
'''
预测相关方法在SteelPricePredict文件夹中
'''
logger = logging.getLogger('django')

media_root = settings.MEDIA_ROOT
data_root = media_root + '/files/data/'

def steelprice(request):
	if not request.user.is_authenticated():
		return HttpResponseRedirect("/login")
	logger.debug(media_root)
	'''
	加载钢材种类，及可选的预测方法
	'''
	logger.debug(steel_type)
	logger.debug(predict_method)
	contentVO={
		'title':'钢材价格预测',
		'state':'success'
	}
	contentVO["steel_type"] = steel_type
	contentVO["predict_method"] = predict_method
	contentVO['time_scale'] = time_scale
	contentVO['info'] = INFO
	contentVO['warning'] = WARNING
	return render(request,'data_import/steelprice.html',contentVO)



def price_history(request):
	if not request.user.is_authenticated():
		return HttpResponseRedirect("/login")
	if request.method == 'POST':
		history_begin =	request.POST.get('history_begin', '')
		history_end =	request.POST.get('history_end', '')
	path = data_root + 'tegang.csv'
	prices = get_history_price(path,history_begin,history_end)

	logger.debug(type(prices.get('price',None)[0]))

	contentVO={
		'title':'钢材历史价格',
		'state':'success'
	}
	contentVO['timeline'] = prices.get('timeline',None)
	contentVO['price'] = prices.get('price',None)
	return HttpResponse(json.dumps(contentVO), content_type='application/json')

def init_models(modelname):
	model = None
	class_name =None
	#通过类名反射相应的类，暂未实例化
	try:
		class_name = model_classname[modelname]
		print(class_name)
		try:
			model = getattr(PredictModels,class_name)
		except:
			print('init model ',class_name,' failed.')
			print(sys.exc_info()[0])
			return {modelname:model}
	except:
		print('no such key name',modelname)
	return {modelname:model}

def price_predict(request):
	if not request.user.is_authenticated():
		return HttpResponseRedirect("/login")
	if request.method == 'POST':
		'''
		获取对应参数
		'''
		steelType =	request.POST.get('steelType', '')
		timeScale =	request.POST.get('timeScale', '')
		typestr =	request.POST.get('typestr', '')
		if typestr != "":
			types = typestr.split(',')
			logger.debug(types)
	'''
	根据参数选择模型
	结果返回预测数据时间跨度，预测值，真实值，score值
	对应不同的模型，每个模型存放在一张字典表中
	外层是由模型名为key的字典表result={"ELM":{"timeline":xxx,"predict_value":xxxx,\
	"true_value":xxxx,"score":xxxx},"SVM":{},"linear_regression":{}}
	'''
	models_result = {}
	path = data_root + 'tegang.csv'
	PRE_DAYS = [5]
	models_data = create_single_model(path,PRE_DAYS)
	logger.debug(len(models_data))
	models = map(init_models,types)
	models = list(models)
	logger.debug(models)
	for index in range(len(models)):
		for method, model in models[index].items():
			if model is not None:
				result = model().predict(models_data[0],0.4)
				models_result[method] = result
	# logger.debug(models_result)

	contentVO={
		'title':'钢材价格预测',
		'state':'success'
	}
	contentVO["result"] = models_result
	return HttpResponse(json.dumps(contentVO), content_type='application/json')
def load_steel_option(request):
	sqlVO={}
	sqlVO["sql"]="SELECT * FROM `data_import_steelprice`"
	# sqlVO["vars"]=["procedure"]

	option_value={}
	procedure_names=models.BaseManage().direct_select_query_sqlVO(sqlVO)
	#print(procedure_names)
	for name in procedure_names:
		option_value[name["procedurename"]]=name["remark"]
	contentVO={
		'title':'ajaxtest请求结果',
		'state':'success',
		'procedure_names':option_value,
	}
	return HttpResponse(json.dumps(contentVO), content_type='application/json')

if __name__ == '__main__':
	# types = []
	# types.append('elm')
	# result = map(execute_models,types)
	# logger.debug(result)
	attrs = get_model_attrs()


from pandas import DataFrame
from pandas import DataFrame
import pandas as pd
import numpy as np
import math
from . import models
from django.shortcuts import render
from django.http import HttpResponse,HttpResponseRedirect,StreamingHttpResponse
import os
import json
import datetime
from django.contrib import auth
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import F
from data_import.forms import UploadFileForm
from . import util
from . import const


def Wushu(x):
    L=np.percentile(x,25)-1.5*(np.percentile(x,75)-np.percentile(x,25))
    U=np.percentile(x,75)+1.5*(np.percentile(x,75)-np.percentile(x,25))
    result=x[(x<U)&(x>L)]
    wushu_clean={}
    wushu_clean["minbook"]=L
    wushu_clean["maxbook"]=U
    wushu_clean["result"]=result
    return wushu_clean
def num_describe(scrapy_records,bookno):
	print("hellohaha");
	if bookno=='"AS"':
		bookno=bookno.split('"')[1]
	#value=bookno.split('"')
	#for i in range(len(value)):
		#value=value[i]
		#if value!='"':
			#print(value)
			#bookno=value
	#print(bookno)
	print(scrapy_records[1:5])
	ivalue_i=[]
	for n in range(len(scrapy_records)):
		ivalue = scrapy_records[n].get(bookno,None)
		if ivalue !=None and ivalue !=0:
			 ivalue=ivalue
			 ivalue_b=str(ivalue)
			 ivalue_valid=ivalue_num(ivalue_b)#小数位数
			 ivalue_i.append(ivalue_valid)
			 ivalue_i.sort(reverse=True)
	ivalue_valid=ivalue_i[0]#取所有有效位数的最大个数
	print(ivalue_valid)		
	for i in range(len(scrapy_records)):
		value = scrapy_records[i].get(bookno,None)
		if value != None :
			scrapy_records[i][bookno] = float(value)			
	frame=DataFrame(scrapy_records)	
	df=frame.sort_values(by=bookno)
	dfr=df[df>0].dropna(how='any')
	#print(dfr['1622324'])
	#print(dfr[bookno].dtype)
	cleanbook=Wushu(dfr[bookno])
	minbook=cleanbook["minbook"]
	maxbook=cleanbook["maxbook"]	
	if(minbook==maxbook):#不符合正态分布规律
		print("no")
		clean=dfr[bookno]		
	else:
		print("yes")
		clean=cleanbook["result"]
		#clean=dfr[bookno]				
	print("minbook")
	print(minbook)
	print("maxbook")
	print(maxbook)
	print(type(clean))
	if clean is not None:
		if(clean.max==clean.min()):
			bc=1
		else:	
			bc=(clean.max()-clean.min())/7
		bcq=math.ceil(bc*1000)/1000
		print(bcq)
		try:
			section=pd.cut(clean,math.ceil((clean.max()-clean.min())/bcq))
			end=pd.value_counts(section,sort=False)/clean.count()
			describe=clean.describe()
		except ValueError as e:
		 	print(e)
	numx=[ele for ele in end.index]
	#numy=[ele for ele in end]
	desx=[ele for ele in describe.index]
	desy=[ele for ele in describe]
	print(numx)
	print(describe)
	#contentVO={
		#'title':'测试',
		#'state':'success'
	#}
	s1=pd.Series(numx)
	d1=getA(s1)
	d2=getB(s1)
	d1_data=[]
	d2_data=[]
	#d3_data=[]
	d4_data=[]
	d1_valid=vaild(d1,ivalue_valid,d1_data)
	for i in range(len(d1_valid)):
		if d1_valid[i]<0:
			d1_valid[i]=0
	d2_valid=vaild(d2,ivalue_valid,d2_data)
	numx1=list(set(d1_valid).union(set(d2_valid)))
	numx2=sorted(numx1)
	print("numx2:")
	print(numx2)
	sections=[]
	numx3=union_section(numx2,sections)
	cut1=pd.cut(clean,numx2)
	end1=pd.value_counts(cut1,sort=False)/clean.count()
	numy=[ele for ele in end1]
	print("end1:")
	print(end1)
	#numy1=vaild(numy,ivalue_valid,d3_data)
	numy1=["%.6f"%(n) for n in numy]
	desy1=vaild(desy,ivalue_valid,d4_data)
	ana_result={}
	ana_result['scope']=numx3
	#print(ana_result['scope'])
	ana_result['num']=numy1
	#contentVO['result']=ana_result
	ana_describe={}
	ana_describe['scopeb']=desx
	ana_describe['numb']=desy1
	#contentVO['describe']=ana_describe
	return ana_result,ana_describe

#可自由选择要进行筛选的条件
def multi_analy(request):
	#print("multi_analy")
	bookno=request.POST.get("bookno").upper();
	SPECIFICATION=request.POST.get("SPECIFICATION");
	OPERATESHIFT=request.POST.get("OPERATESHIFT");
	OPERATECREW=request.POST.get("OPERATECREW");
	station=request.POST.get("station");
	time1=request.POST.get("time1");
	time2=request.POST.get("time2");
	if SPECIFICATION !='blank':
		if SPECIFICATION =='null':
			sentence_SPECIFICATION="SPECIFICATION is null"
		else:	
			sentence_SPECIFICATION= "  SPECIFICATION='"+SPECIFICATION+"'"
	else:
		sentence_SPECIFICATION=''
	if OPERATESHIFT !='blank':
		sentence_OPERATESHIFT=" and OPERATESHIFT='"+OPERATESHIFT+"'"
	else:
		sentence_OPERATESHIFT=''
	if OPERATECREW !='blank':
		sentence_OPERATECREW=" and OPERATECREW='"+OPERATECREW+"'"
	else:
		sentence_OPERATECREW=''
	if station !='blank':
		sentence_station=" and station='"+station+"'"
	else:
		sentence_station=''
	if time1 != '' and time2!='':
		sentence_time="and to_char(MSG_DATE_PLAN,'yyyy-mm-dd')>'"+time1+"'and to_char(MSG_DATE_PLAN,'yyyy-mm-dd')<'"+time2+"'"
	else:
		sentence_time=''
	sentence="SELECT HEAT_NO,"+bookno+",MSG_DATE_PLAN FROM qg_user.PRO_BOF_HIS_ALLFIELDS WHERE HEAT_NO>'1500000'"+sentence_SPECIFICATION+sentence_OPERATESHIFT+sentence_OPERATECREW+sentence_station+sentence_time
	#sentence="SELECT HEAT_NO,"+bookno+" FROM qg_user.PRO_BOF_HIS_ALLFIELDS WHERE "+sentence_SPECIFICATION+sentence_OPERATESHIFT+sentence_OPERATECREW+sentence_station
	print(sentence)
	sqlVO={}
	sqlVO["db_name"]="l2own"
	sqlVO["sql"]=sentence
	#print(sqlVO["sql"])
	scrapy_records=models.BaseManage().direct_select_query_sqlVO(sqlVO)
	#print(scrapy_records[:5])
	contentVO={
		'title':'测试',
		'state':'success',
	}
	ana_result,ana_describe=num_describe(scrapy_records,bookno)
	contentVO['result']=ana_result
	contentVO['describe']=ana_describe
	return HttpResponse(json.dumps(contentVO),content_type='application/json')
#去括号取左侧的数
def getA(s):
    s0 = list(s)
    data = []
    for a in s0:
        a1 = a.split(',')
        if len(a1)==1:
            data.append(a1[0][1:])
        else:
            data.append(a1[0][1:])
    return data
#去括号取右侧的数    
def getB(s):
    s0 = list(s)
    data = []
    for a in s0:
        a1 = a.split(',')
        if len(a1)==1:
            data.append(a1[1][:-1])
        else:
            data.append(a1[1][:-1])
    return data	
#def vaild(lis,ivalue_valid,data):
    #for i in range(len(lis)):
        #shu=lis[i]
        #shua=float(shu)
        #shub=round(shua,ivalue_valid)
        #data.append(shub)
    #return data 
def union_section(section_point,sections):#拼接区间
    for i in range(len(section_point)):
        section=None
        if i<len(section_point)-1:
            section='('+str(section_point[i])+','+str(section_point[i+1])+']'
            sections.append(section)
    return sections 
def ivalue_num(num):#判断有效位数
    a=str(num)
    if(a.isdigit()):
        ivalue_valid=0
    else:
        ivalue_valid=len(a.split('.')[1])
    return  ivalue_valid   
def vaild(lis,ivalue_valid,data):#取有效位数
    for i in range(len(lis)):
        shu=lis[i]
        if ivalue_valid==0:
            shua=int(float(shu))
            data.append(shua)
        else:    
            shua=float(shu)
            shub=round(shua,ivalue_valid)
            data.append(shub)
    return data 
#从数据库动态加载钢种
def paihao_getGrape(request):
	print("计划牌号")
	sqlVO={}
	sqlVO["db_name"]="l2own"
	#sqlVO["sql"]="select distinct SPECIFICATION from qg_user.PRO_BOF_HIS_ALLFIELDS order by SPECIFICATION";
	sqlVO["sql"]="select SPECIFICATION  from pro_bof_his_allfields group by SPECIFICATION order by count(*) DESC"
	print(sqlVO["sql"])
	scrapy_records=models.BaseManage().direct_select_query_sqlVO(sqlVO)
	frame=DataFrame(scrapy_records)
	#print(frame['SPECIFICATION'])
	contentVO={
		'title':'测试',
		'state':'success'
	}
	grape=[ele for ele in frame['SPECIFICATION']]
	#print(grape)
	contentVO['result']=grape
	return HttpResponse(json.dumps(contentVO),content_type='application/json')
from . import zhuanlu
def no_lond_to(request):
	contentVO={
		'title':'测试',
		'state':'success'
	}
	ana_result={}
	ana_result=zhuanlu.PRO_BOF_HIS_ALLFIELDS_B
	contentVO['no_procedure_names']=ana_result
	#print(contentVO)
	return HttpResponse(json.dumps(contentVO),content_type='application/json')
def little_lond_to(request):
	contentVO={
		'title':'测试',
		'state':'success'
	}
	ana_result={}
	ana_result=zhuanlu.PRO_BOF_HIS_ALLFIELDS_C
	contentVO['little_procedure_names']=ana_result
	#print(contentVO)
	return HttpResponse(json.dumps(contentVO),content_type='application/json')	
def describe_ha(request):
	littleno=request.POST.get("littleno").upper();
	sqlVO={}
	sqlVO["db_name"]="l2own"
	sqlVO["sql"]="SELECT HEAT_NO,"+littleno+" FROM qg_user.PRO_BOF_HIS_ALLFIELDS"
	scrapy_records=models.BaseManage().direct_select_query_sqlVO(sqlVO)
	# print(bookno)
	# print(scrapy_records[:5])
	contentVO={
		'title':'分析结果绘图',
		'state':'success',
	}
	for i in range(len(scrapy_records)):
		value = scrapy_records[i].get(littleno,None)
		if value != None :
			scrapy_records[i][littleno] = float(value)
	frame=DataFrame(scrapy_records)	
	df=frame.sort_values(by=littleno)
	dfr=df[df>0].dropna(how='any')	
	cleanbook=Wushu(dfr[littleno])
	clean=cleanbook["result"]
	describe=clean.describe()
	desx=[ele for ele in describe.index]
	desy=[ele for ele in describe]
	desy1=["%.2f"%(n) for n in desy]
	print(desx)
	print(desy)
	ana_describe={}
	ana_describe['scopeb']=desx
	ana_describe['numb']=desy1

	return HttpResponse(json.dumps(ana_describe),content_type='application/json')

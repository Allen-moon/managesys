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
import csv
from decimal import *
from docx import Document
from docx.shared import Inches
from . import batchprocess
import time
from . import bof_config


#计算转炉质量及含量
def qualityfields(request):
	print('hello')
	#print("cost_success")
	heat_no=request.POST.get("heat_no");
	SPECIFICATION_ask=str(request.POST.get("SPECIFICATION"));#钢种的筛选要求，native/all
	OPERATECREW_ask=str(request.POST.get("OPERATECREW"));#班别的筛选要求native/all/A/B/C
	time1=request.POST.get("starttime");
	time2=request.POST.get("endtime");

	contentVO={
		'title':'测试',
		'state':'success',
	}

	xasis_fieldname_ch=['C含量','SI含量','MN含量','P含量','S含量','重量','温度']
	xasis_fieldname=['C','SI','MN','P','S','STEELWGT','FINAL_TEMP_VALUE']
	#先查出当前炉次实际所属钢种及班别
	sqlVO={}
	sqlVO["db_name"]="l2own"
	sqlVO["sql"]="SELECT HEAT_NO,SPECIFICATION,OPERATECREW FROM qg_user.PRO_BOF_HIS_ALLFIELDS WHERE HEAT_NO='"+heat_no+"'";
	scrapy_records=models.BaseManage().direct_select_query_sqlVO(sqlVO)
	if len(scrapy_records)==0:#无该炉次号
			contentVO['state']='error'
			return HttpResponse(json.dumps(contentVO),content_type='application/json')

	actual_SPECIFICATION=scrapy_records[0].get('SPECIFICATION',None)
	actual_OPERATECREW=scrapy_records[0].get('OPERATECREW',None)
	
	#确认实际筛选语句		
	str_select=""
	if SPECIFICATION_ask=='native' and actual_SPECIFICATION !=None:#本钢种且本钢种不为空
		str_select=str_select+" and SPECIFICATION = '"+str(actual_SPECIFICATION)+"'"

	if OPERATECREW_ask=='native' and actual_OPERATECREW !=None:
		str_select=str_select+" and OPERATECREW = '"+str(actual_OPERATECREW)+"'"
	elif OPERATECREW_ask=='all':
		pass
	else:
		str_select=str_select+" and OPERATECREW = '"+OPERATECREW_ask+"'"


	# 当前时间
	time_now=time.strftime('%Y-%m-%d',time.localtime(time.time()))
	#将时间为空时的值进行转换
	if time1=='':
		time1='2016-01-01'
	if time2=='':
		time2=time_now

	# print(time1,time2)
	#时间筛选条件
	if time1=='2016-01-01' and time2==time_now:#走缓存
		pass
	else:#执行普通分析
		str_select=str_select+" and to_char(MSG_DATE_PLAN,'yyyy-mm-dd')>='"+time1+"' and to_char(MSG_DATE_PLAN,'yyyy-mm-dd')<='"+time2+"'"


	#对任意个数字段进行字符串拼接
	field_sql=''
	for i in range(len(xasis_fieldname)):
		field_sql=field_sql+',nvl('+xasis_fieldname[i]+',0) as '+xasis_fieldname[i]

	sqlVO={}
	sqlVO["db_name"]="l2own"
	# sqlVO["sql"]="SELECT HEAT_NO,nvl(TOTAL_SLAB_WGT,0) as TOTAL_SLAB_WGT,nvl(LDG_TOTAL_SLAB_WGT,0) as LDG_TOTAL_SLAB_WGT ,nvl(STEEL_SLAG,0) as STEEL_SLAG FROM qg_user.PRO_BOF_HIS_ALLFIELDS where heat_no='"+heat_no+"'";
	sqlVO["sql"]="SELECT HEAT_NO "+field_sql+" FROM qg_user.PRO_BOF_HIS_ALLFIELDS WHERE HEAT_NO='"+heat_no+"'";
	print('筛选语句',sqlVO["sql"])
	scrapy_records=models.BaseManage().direct_select_query_sqlVO(sqlVO)

	yaxis=[]#存放单炉次的字段值
	for i in range(len(xasis_fieldname)):
		value = scrapy_records[0].get(xasis_fieldname[i],None)
		if value != None :
			pass
		else:
			value = 0
		yaxis.append(float(value))

	print('xasis_fieldname',xasis_fieldname)
	print('yaxis',yaxis)
	offset_result=offset(xasis_fieldname,yaxis,str_select)#计算偏离程度函数的返回值
	qualitative_offset_result=qualitative_offset(offset_result)#对偏离程度进行定性判断
	offset_resultlist=[]#存储带百分号的偏离程度
	for n in list(offset_result):
		if n==None:
			offset_resultlist.append(n)
		else:
			offset_resultlist.append("%.2f%%"%(n*100))
	# offset_resultlist=["%.2f%%"%(n*100) for n in list(offset_result)]
	print('offset_result',offset_result)
	print('offset_resultlist',offset_resultlist)


	ana_result={}
	ana_result['heat_no']=heat_no#炉次号
	ana_result['xname']=xasis_fieldname_ch#字段中文名字
	ana_result['xEnglishname']=xasis_fieldname#字段英文名字
	# ana_result['danwei']=danwei#字段的数值单位
	ana_result['str_select']=str_select
	ana_result['yvalue']=yaxis#该炉次字段的实际值
	ana_result['offset_result_nopercent']=offset_result#各字段的偏离程度值（不带百分比）
	ana_result['offset_result']=offset_resultlist#各字段的偏离程度值（带百分比）
	ana_result['qualitative_offset_result']=qualitative_offset_result#各字段的偏离程度定性判断结果

	contentVO['result']=ana_result
	return HttpResponse(json.dumps(contentVO),content_type='application/json')

def offset(xasis_fieldname,yaxis,str_select):
	offset_result=[]
	sqlVO={}
	sqlVO["db_name"]="l2own"
	# print('len(xasis_fieldname)',len(xasis_fieldname))

	parameters=["MAX_VALUE","MIN_VALUE","DESIRED_VALUE","STANDARD_DEVIATION",'NUMERICAL_LOWER_BOUND','NUMERICAL_UPPER_BOUND','IF_FIVENUMBERSUMMARY']
	for i in range (len(xasis_fieldname)):#实际计算范围为从0到len(xasis_fieldname)-1
		# if yaxis[i]==0 or yaxis[i] is None:
		# 	offset_result.append(None)
		# 	continue;
		sqlVO["sql"]="SELECT MAX_VALUE,MIN_VALUE,DESIRED_VALUE,STANDARD_DEVIATION,NUMERICAL_LOWER_BOUND,NUMERICAL_UPPER_BOUND,IF_FIVENUMBERSUMMARY FROM qg_user.PRO_BOF_HIS_ALLSTRUCTURE where DATA_ITEM_EN = \'"+xasis_fieldname[i]+"\'"
		# print(sqlVO["sql"])
		scrapy_records=models.BaseManage().direct_select_query_sqlVO(sqlVO)
		# print(scrapy_records)
		# print(temp_array)
		# print(yaxis[i])
		# print(isinstance(yaxis[i],float))#判断数据类型
		for j in range (len(parameters)):
			value = scrapy_records[0].get(parameters[j],None)
			if value != None and value != 'null':
				scrapy_records[0][parameters[j]] = float(value)


		if str_select=='':#相当于无筛选条件,直接根据最大最小值计算偏离程度
			print('enter 缓存')
			#如果实际值大于最大值，则按最大值计算，偏离程度为50% ; 如果实际值小于最小值，则按最小值处理。偏离程度为-50%
			if float(yaxis[i])>scrapy_records[0]['MAX_VALUE']:
				adjusted_yaxis=scrapy_records[0]['MAX_VALUE']
			elif float(yaxis[i])<scrapy_records[0]['MIN_VALUE']:
				adjusted_yaxis=scrapy_records[0]['MIN_VALUE']
			else :
				adjusted_yaxis=float(yaxis[i])


			try:
				# temp_value=(float(yaxis[i])-scrapy_records[0]['DESIRED_VALUE'])/(scrapy_records[0]['MAX_VALUE']-scrapy_records[0]['MIN_VALUE'])
				temp_value=(adjusted_yaxis-scrapy_records[0]['MIN_VALUE'])/(scrapy_records[0]['MAX_VALUE']-scrapy_records[0]['MIN_VALUE'])-0.5
			except:
				temp_value=None
			offset_result.append(temp_value)

		else:#有筛选条件,需要动态经过上下限、五数等清洗后计算最大最小值
			print('执行普通程序，不走缓存')
			#bound_select:上下限筛选条件
			bound_select =' and '+xasis_fieldname[i]+'>='+str(scrapy_records[0]['NUMERICAL_LOWER_BOUND']) +' and '+xasis_fieldname[i]+'<='+str(scrapy_records[0]['NUMERICAL_UPPER_BOUND'])
			sqlVO1={}
			sqlVO1["db_name"]="l2own"
			sqlVO1["sql"]="SELECT HEAT_NO,"+xasis_fieldname[i]+" FROM qg_user.PRO_BOF_HIS_ALLFIELDS where heat_no>'1500000'"+str_select+bound_select
			print(sqlVO1["sql"])
			scrapy_records1=models.BaseManage().direct_select_query_sqlVO(sqlVO1)

			if len(scrapy_records1)<50:#对比数据条数不足100条，表示无法进行偏离程度计算
				offset_result.append(None)
				continue

			for k in range(len(scrapy_records1)):
					value = scrapy_records1[k].get(xasis_fieldname[i],None)
					if value != None :
						scrapy_records1[k][xasis_fieldname[i]] = float(value)
			frame=DataFrame(scrapy_records1)
			df=frame.sort_values(by=xasis_fieldname[i])
			# print(df)
			#进行五数清洗
			if scrapy_records[0]['IF_FIVENUMBERSUMMARY']==1:
				
				clean=Wushu(df[xasis_fieldname[i]])['result']
			else:
				clean=df[xasis_fieldname[i]]
			print('五数清洗后的数据条数：',len(clean))
			if len(clean)<50:#数据不足100条
				offset_result.append(None)
				continue
			# print('clean结果',clean)

			# dataclean_result={}
			avg_value=np.mean(clean)
			print("期望值",avg_value)
			#标准差
			std_value=np.std(clean)
			print("标准差",std_value)
			#方差
			# var_value=np.var(clean)
			# print("方差",var_value)
			#normx,normy=Norm_dist(avg_value,var_value)
			print("min",clean.min())
			print("max",clean.max())

			# temp_array=data_clean(scrapy_records1,xasis_fieldname[i])#字段清洗后统计情况
			# print(temp_array)
			print(yaxis[i])
			# print(isinstance(yaxis[i],float))#判断数据类型

			#如果实际值大于最大值，则按最大值计算，偏离程度为50% ; 如果实际值小于最小值，则按最小值处理。偏离程度为-50%
			if float(yaxis[i])>clean.max():
				adjusted_yaxis=clean.max()
			elif float(yaxis[i])<clean.min():
				adjusted_yaxis=clean.min()
			else :
				adjusted_yaxis=float(yaxis[i])


			try:
				temp_value=(adjusted_yaxis-avg_value)/(clean.max()-clean.min())
			except:
				temp_value=None
			offset_result.append(temp_value)


	print('offset_result',offset_result)
	return offset_result

#去括号取左侧的数（计算概率分布时需要用到）
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

#去括号取右侧的数（计算概率分布时需要用到）    
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

#拼接区间（计算概率分布时需要用到） 
def union_section(section_point,sections):
    for i in range(len(section_point)):
        section=None
        if i<len(section_point)-1:
            section='('+str(section_point[i])+','+str(section_point[i+1])+']'
            sections.append(section)
    return sections 






#对偏离程度进行定性判断：高，偏高，正常范围，偏低，低，极端异常
def qualitative_offset(offset_result):
	#偏离程度定性标准，例如-10%~10%为正常，10%~30%为偏高，30%以上为高
	# qualitative_standard=[0.2,0.35]
	qualitative_standard=bof_config.qualitative_standard
	qualitative_offset_result=[]
	for i in range(len(offset_result)):
		if offset_result[i]==None:
			qualitative_offset_result.append('数据量少无法计算')
		elif abs(float(offset_result[i]))<=qualitative_standard[0]:
			qualitative_offset_result.append('正常')
		elif abs(float(offset_result[i]))<=qualitative_standard[1]:
			if float(offset_result[i])>0:#偏高
				qualitative_offset_result.append('偏高')
			else:#偏低
				qualitative_offset_result.append('偏低')
		else:#取消数据异常情况
			if float(offset_result[i])>0:#高
				qualitative_offset_result.append('高')
			else:
				qualitative_offset_result.append('低')		
	return  qualitative_offset_result



#从数据库动态加载钢种
def getGrape(request):
	sqlVO={}
	sqlVO["db_name"]="l2own"
	sqlVO["sql"]="select distinct gk_no from qg_user.PRO_BOF_HIS_ALLFIELDS order by gk_no";
	print(sqlVO["sql"])
	scrapy_records=models.BaseManage().direct_select_query_sqlVO(sqlVO)
	frame=DataFrame(scrapy_records)
	#print(frame['GK_NO'])
	contentVO={
		'title':'测试',
		'state':'success'
	}
	grape=[ele for ele in frame['GK_NO']]
	#print(grape)
	contentVO['result']=grape
	return HttpResponse(json.dumps(contentVO),content_type='application/json')

#进行五数分析法
def Wushu(x):
    L=np.percentile(x,25)-1.5*(np.percentile(x,75)-np.percentile(x,25))
    U=np.percentile(x,75)+1.5*(np.percentile(x,75)-np.percentile(x,25))
    result=x[(x<U)&(x>L)]
    wushu_clean={}
    wushu_clean["minbook"]=L
    wushu_clean["maxbook"]=U
    wushu_clean["result"]=result
    return wushu_clean



#判断有效位数
def ivalue_num(num):
    a=str(num)
    if(a.isdigit()):
        ivalue_valid=0
    else:
        ivalue_valid=len(a.split('.')[1])
    return  ivalue_valid   

#取有效位数
def vaild(lis,ivalue_valid,data):
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


#同时计算概率分布和正态分布
#同时计算概率分布和正态分布
from scipy.stats import norm
def probability_distribution(request):
	print("同时计算概率直方图和正态分布图！")

	#获取信息
	heat_no=request.POST.get("heat_no");#炉次号
	bookno=request.POST.get("fieldname_english").upper();#字段英文名
	fieldname_chinese=request.POST.get("fieldname_chinese")#字段中文名
	offset_value=request.POST.get("offset_value");#偏离值（带百分号）
	# offset_value=float(offset_value_temp[1:-1])/100
	actual_value=float(request.POST.get("actual_value"))#实际值
	coloum_number=int(request.POST.get("coloum_number"))#定义概率直方图的柱状个数
	str_select=str(request.POST.get("str_select"));#筛选条件
	if str_select==str(None):#表示没有筛选条件
		str_select=''

	#查询上下限及是否五数清洗
	sqlVO={}
	sqlVO["db_name"]="l2own"
	sqlVO["sql"]="SELECT NUMERICAL_LOWER_BOUND,NUMERICAL_UPPER_BOUND,IF_FIVENUMBERSUMMARY FROM qg_user.PRO_BOF_HIS_ALLSTRUCTURE where DATA_ITEM_EN = \'"+bookno+"\'"
	# print(sqlVO["sql"])
	scrapy_records=models.BaseManage().direct_select_query_sqlVO(sqlVO)
	NUMERICAL_LOWER_BOUND=scrapy_records[0].get('NUMERICAL_LOWER_BOUND',None)
	NUMERICAL_UPPER_BOUND=scrapy_records[0].get('NUMERICAL_UPPER_BOUND',None)
	IF_FIVENUMBERSUMMARY=scrapy_records[0].get('IF_FIVENUMBERSUMMARY',None)

	bound_select =' and '+bookno+'>='+str(scrapy_records[0]['NUMERICAL_LOWER_BOUND']) +' and '+bookno+'<='+str(scrapy_records[0]['NUMERICAL_UPPER_BOUND'])

	#需要返回的计算结果
	contentVO={
	'title':'测试',
	'state':'success'
	}

	#进行数据库查询
	sqlVO={}
	sqlVO["db_name"]="l2own"
	sqlVO["sql"]="SELECT HEAT_NO,"+bookno+" FROM qg_user.PRO_BOF_HIS_ALLFIELDS WHERE HEAT_NO>'1500000'"+str_select+bound_select
	# print(sqlVO["sql"])
	scrapy_records=models.BaseManage().direct_select_query_sqlVO(sqlVO)
	print('len(scrapy_records):',len(scrapy_records))
	if len(scrapy_records)<50:
		contentVO['state']='error'
		return HttpResponse(json.dumps(contentVO),content_type='application/json')

	#进行数据清洗
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
	# print(ivalue_valid)		
	for i in range(len(scrapy_records)):
		value = scrapy_records[i].get(bookno,None)
		if value != None :
			scrapy_records[i][bookno] = float(value)			
	frame=DataFrame(scrapy_records)	
	df=frame.sort_values(by=bookno)
	# dfr=df[df>0].dropna(how='any')

	#进行五数清洗
	if float(IF_FIVENUMBERSUMMARY)==1:
		clean=Wushu(df[bookno])['result']
	else:
		clean=df[bookno]
	print('五数清洗后的数据条数：',len(clean))

	if len(clean)<50:#数据不足100条
		contentVO['state']='error'
		return HttpResponse(json.dumps(contentVO),content_type='application/json')

	if clean is not None:
		if(clean.max==clean.min()):
			bc=1
		else:	
			bc=(clean.max()-clean.min())/coloum_number
		bcq=math.ceil(bc*1000)/1000
		# print(bcq)
		try:
			#计算概率直方分布
			section=pd.cut(clean,math.ceil((clean.max()-clean.min())/bcq))
			end=pd.value_counts(section,sort=False)/clean.count()
			describe=clean.describe()#参数统计信息
		except ValueError as e:
		 	print(e)
	numx=[ele for ele in end.index]
	#numy=[ele for ele in end]
	desx=[ele for ele in describe.index]
	desy=[ele for ele in describe]
	# print(numx)
	# print(describe)

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
	# print("numx2:")
	# print(numx2)
	sections=[]
	numx3=union_section(numx2,sections)
	cut1=pd.cut(clean,numx2)
	end1=pd.value_counts(cut1,sort=False)/clean.count()
	numy=[ele for ele in end1]
	# print("end1:")
	# print(end1)
	#numy1=vaild(numy,ivalue_valid,d3_data)
	numy1=["%.6f"%(n) for n in numy]
	print("x轴:")
	print(numx3)
	print("y轴:")
	print(numy1)
	desy1=vaild(desy,ivalue_valid,d4_data)

	#计算正态分布起始--------------------------------------------------
	#desy1内容依次为count、mean、std、min、25%、50%、75%、max
	aa=(desy1[7]-desy1[3])/50
	normx_array = np.arange(desy1[3],desy1[7],aa)  
	normy_array = norm.pdf(normx_array,desy1[1],desy1[2])
	#转换格式，限制小数位数
	normx=["%.4f"%(n) for n in list(normx_array)]
	normy=["%.7f"%(n) for n in list(normy_array)]
	#计算正态分布结束---------------------------------------------------------

	ana_result={}
	#概率分布：x轴：scope,y轴：num
	ana_result['scope']=numx3#区间数组
	ana_result['num']=numy1#区间对应值

	#正态分布：x轴：normx,y轴：numy
	ana_result['normx']=normx
	ana_result['normy']=normy

	#统计参数：内容依次为count、mean、std、min、25%、50%、75%、max
	ana_describe={}
	ana_describe['scopeb']=desx
	ana_describe['numb']=desy1
	


	#---------判断该炉次该字段在历史正态分布曲线中距离最近的取样点-----------
	temp=float(normx[0])
	temp_index=0
	for i in range (0,len(normx)-1):
		former=float(normx[i])
		latter=float(normx[i+1])
		#print(former,latter)
		if (actual_value>former) & (actual_value<=latter):
			temp_index=i
			if abs(actual_value-former)<abs(actual_value-latter):
				temp=former
			else:
				temp=latter
			break;
	print(temp_index,temp)

	#单炉次的一些信息
	base_result={}
	base_result['fieldname']=bookno#字段英文名
	base_result['fieldname_chinese']=fieldname_chinese#字段中文名
	base_result['actual_value']=actual_value#自身值
	# base_result['offset_value']="%.2f%%"%(offset_value*100)#偏离程度(当offset_value为小数形式时可用此行代码)
	base_result['offset_value']=offset_value#偏离程度(当offset_value已经为百分号形式时可用此行代码)
	# return base_result
	base_result['match_index']=temp_index#对应序号
	base_result['match_value']=str("%.4f"%(temp))#距离最近的值,由于在之前将其转化为float类型进行过数据对比，例如，123.0000被默认识别为123，当再次转化为str类型时，则也成了‘123’，因此就与normx的值对不上了
	

	contentVO['ana_result']=ana_result#概率分布及正态分布
	contentVO['ana_describe']=ana_describe#统计数据的描述
	contentVO['base_result']=base_result#该炉次的相关信息
	# print('contentVO',contentVO)
	return HttpResponse(json.dumps(contentVO),content_type='application/json')

from . import batchprocess
'''
单炉次字段质量回溯
网页
'''
#单炉次质量追溯（非暴力，在界面上输出）-----------------------------------------
#界面上追溯时程序入口
def quality_singlefurnace_regression_analyse(request):
	print("quality_singlefurnace_regression_analyse")

	result = json.loads(request.POST.get("result"));

	str_cause=quality_regression_analyse_to(result)

	contentVO={
		'title':'测试',
		'state':'success',
		'str_cause':str_cause
	}				
	return HttpResponse(json.dumps(contentVO),content_type='application/json')	



def quality_regression_analyse_to(result):  
	prime_cost = result['heat_no'];
	str_select = result['str_select'];#筛选条件 

	n=0#n用来指示当前问题字段的个数
	str_cause='本炉次为'+str(prime_cost)+'，问题字段因素分析如下：\n'#存放分析结果

	xasis_fieldname_ch=result['xname']#中文名
	xasis_fieldname_en = result['xEnglishname']#英文名
	# danwei = result['danwei']#单位
	yaxis_single = result['yvalue']#实际值
	offset_result_nopercent = result['offset_result_nopercent']#不带百分号偏离程度（会有none）
	qualitative_offset_result = result['qualitative_offset_result']#各字段的偏离程度定性判断结果

	for i in range(len(xasis_fieldname_en)):
		# print("进行%s的追溯"%(xasis_fieldname_en[i]))

		if offset_result_nopercent[i] ==None:#表示数据不足无法计算
			continue

		xaxis_chinese=xasis_fieldname_ch[i];
		field=xasis_fieldname_en[i];
		single_value=yaxis_single[i];
		offset_value=offset_result_nopercent[i];
		offset_value_abs="%.2f%%"%(abs(float(offset_value))*100)
		qualitative_offset_result_single=qualitative_offset_result[i];

		sql = "select DATA_ITEM_EN,IF_FIVENUMBERSUMMARY,NUMERICAL_LOWER_BOUND,NUMERICAL_UPPER_BOUND from QG_USER.PRO_BOF_HIS_ALLSTRUCTURE WHERE  DATA_ITEM_EN = '"+field+"'"
		sqlVO={}
		sqlVO["db_name"]="l2own"
		sqlVO["sql"] = sql
		scrapy_records = models.BaseManage().direct_select_query_sqlVO(sqlVO)
		NUMERICAL_LOWER_BOUND=scrapy_records[0].get('NUMERICAL_LOWER_BOUND',None)#下限
		NUMERICAL_UPPER_BOUND=scrapy_records[0].get('NUMERICAL_UPPER_BOUND',None)#上限
		# if single_value==0:#实际值为0的字段在暴力追溯中暂时不分析，在网页中根据上下限进行处理
		# 	# str_des='本炉次'+prime_cost+'的'+xaxis_chinese+'数据异常！\n' 	
		# 	continue


		if single_value<float(NUMERICAL_LOWER_BOUND) or single_value>float(NUMERICAL_UPPER_BOUND):#实际值在上下限范围之外，表示数据异常；实际值在上下限之间，但在最大最小值之外，在计算偏离程度时（offeset()）按照最大最小值计算
			str_cause=str_cause+'【'+str(n+1)+'】'+xaxis_chinese+'数据异常！\n' 
			n=n+1
			continue
		elif abs(float(offset_value))<=bof_config.single_doretrospect:#偏离度小于20%的设定为正常
			# str_des='本炉次'+prime_cost+'的'+xaxis_chinese+qualitative_offset_result_single+',实际值为'+str(single_value)+danwei[i]+',偏离度为'+offset_value+'。\n'      
			continue

		#中文名、偏离程度定性描述、带百分号的偏离程度绝对值、回归系数
		En_to_Ch_result_score,offset_result_nature,offset_value_single_cof,regression_coefficient_result=analy_cof(prime_cost,field,single_value,offset_value,str_select);		
		if 	En_to_Ch_result_score==None:
			# str_des='本炉次'+prime_cost+'的'+xaxis_chinese+qualitative_offset_result_single+',实际值为'+str(single_value)+danwei[i]+'，但进行回归分析时相关字段无数据！'

			continue
		else:
			# str_des='本炉次'+prime_cost+'的'+xaxis_chinese+qualitative_offset_result_single+',实际值为'+str(single_value)+danwei[i]+',偏离度为'+offset_value+'。通过数据相关性分析发现，导致该问题的原因是:\n'      
			str_cause= str_cause+'【'+str(n+1)+'】'+xaxis_chinese+qualitative_offset_result_single+offset_value_abs+'：'      
			n=n+1
			for i in range(len(En_to_Ch_result_score)):
				str_cause=str_cause+'[原因'+str(i+1)+']'+En_to_Ch_result_score[i]+offset_result_nature[i]+offset_value_single_cof[i]+'；'
			str_cause=str_cause+'\n'
	if n==0:
		str_cause='本炉次为'+str(prime_cost)+'，无当前历史条件下的追溯结果。\n'
	# print('追溯结果：',str_cause)
	return 	str_cause		

from . import zhuanlu
def  analy_cof(prime_cost,field,single_value,offset_value,str_select):
	#从数据库读取相关字段并按照相关系数绝对值由大到小排序
	print('进行%s炉次下的%s字段的追溯'%(prime_cost,field))
	sqlVO={}
	sqlVO["db_name"]="l2own"
	sqlVO["sql"]="SELECT * FROM pro_bof_his_relation_cof where OUTPUTFIELD='"+field +"'order by abs(COF) desc"
	#print(sqlVO["sql"])
	scrapy_records_relation=models.BaseManage().direct_select_query_sqlVO(sqlVO)
	#print(scrapy_records)
	length_result1=len(scrapy_records_relation)
	if length_result1==0:#即无相关性字段
		return None,None,None,None


	xasis_fieldname=[]#字段英文名字数组
	correlation_coefficient=[]#字段相关系数值数组
	str_sql=''
	for i in range(length_result1):
		xasis_fieldname.append(scrapy_records_relation[i].get('MIDDLEFIELD', None))
		correlation_coefficient.append(scrapy_records_relation[i].get('COF', None))
		str_sql=str_sql+','+scrapy_records_relation[i].get('MIDDLEFIELD', None)
	
	#取相关字段实际值
	sqlVO={}
	sqlVO["db_name"]="l2own"
	sqlVO["sql"]="SELECT HEAT_NO" +str_sql+" FROM qg_user.PRO_BOF_HIS_ALLFIELDS where HEAT_NO='"+prime_cost+"'";
	print(sqlVO["sql"])
	scrapy_records_actual=models.BaseManage().direct_select_query_sqlVO(sqlVO)
	yaxis=[]#各相关性字段实际值
	for i in range(length_result1):
		value = scrapy_records_actual[0].get(xasis_fieldname[i],None)
		if value != None :
			scrapy_records_actual[0][xasis_fieldname[i]] = Decimal(value)
		else:
			value = 0#将空值None暂时以0填充
		yaxis.append(value)
	# frame=DataFrame(scrapy_records_actual)
	# print("frame",frame)	
	print("yaxis",yaxis)

	offset_degree=offset(xasis_fieldname,yaxis,str_select)
	# print("字段名字：")
	# print(xasis_fieldname)
	# print("相关性：")
	# print(correlation_coefficient)
	# print("偏离程度")
	# print(offset_degree)
	xasis_fieldname_result=[]#字段英文名字数组
	correlation_coefficient_result=[]#字段回归系数值数组
	offset_degree_result=[]#偏离程度值
	
	j=0#标志位，表示当前筛选后的有效字段个数
	#字段偏离高，则正相关应对应偏高，负相关应对应偏低
	if float(offset_value)>=0:
		for i in range(length_result1):
			if j>=8:#取筛选后相关性最大的八个因素字段
				break
			if offset_degree[i]==None  or abs(offset_degree[i])<=0.2 or yaxis[i]==0 :#由于数据清洗的问题，暂且将NB字段如此处理，因为NB字段的所有数据均相同，导致数据清洗时将所有数据都清除了
				continue
			if float(correlation_coefficient[i]) * float(offset_degree[i]) >=0:
				j+=1
				xasis_fieldname_result.append(xasis_fieldname[i])
				correlation_coefficient_result.append(correlation_coefficient[i])
				offset_degree_result.append(offset_degree[i])
	else:
		for i in range(length_result1):
			if j>=8:
				break
			if offset_degree[i]==None  or abs(offset_degree[i])<=0.2 or yaxis[i]==0:
				continue
			if float(correlation_coefficient[i]) * float(offset_degree[i]) <=0:
				j+=1
				xasis_fieldname_result.append(xasis_fieldname[i])
				correlation_coefficient_result.append(correlation_coefficient[i])
				offset_degree_result.append(offset_degree[i])
	
	#正负相关筛选后的相关字段个数
	print('正负相关筛选后的相关字段个数',len(xasis_fieldname_result))
	print("8个字段英文名字：")
	print(xasis_fieldname_result)

	if len(xasis_fieldname_result) == 0:
		return None,None,None,None

	#计算回归系数:regression_coefficient[0]表示各回归值，regression_coefficient[1]表示截距;1表示在regression中进行标准化，0表示不进行标准化
	regression_coefficient=batchprocess.regression(field,xasis_fieldname_result,1)
	if regression_coefficient== False:
		return None,None,None,None

	#查询转炉工序字段名中英文对照
	ana_result={}
	ana_result=zhuanlu.PRO_BOF_HIS_ALLFIELDS
	En_to_Ch_result=[]
	for i in range(len(xasis_fieldname_result)):
		En_to_Ch_result.append(ana_result[xasis_fieldname_result[i]])
	# print("字段中文名字")
	# print(En_to_Ch_result)
	# print("8个字段英文名字：")
	# print(xasis_fieldname_result)
	# print("相关性系数")
	# print(correlation_coefficient_result)
	# print("回归系数")
	# print(regression_coefficient[0])
	# print("偏离程度")
	# print(offset_degree_result)

	#zip压缩:中文名、英文名、偏离程度、回归系数;注：python3之后zip函数返回的是迭代值，需要list强转
	L_zip=list(zip(En_to_Ch_result,xasis_fieldname_result,offset_degree_result,regression_coefficient[0],correlation_coefficient_result))
	print('L_zip:',list(L_zip))
	#按照回归系数进行排序(从大到小)
	L_zip.sort(key=lambda x:x[3],reverse=True)
	print('按照回归系数排序后的字段：',L_zip)
	#取回归系数前二的字段
	L_zip=L_zip[0:2]#表示取0和1
	print('取前二个字段时的实际字段个数：',len(L_zip))
	#解压缩
	L_unzip=list(zip(*L_zip))
	En_to_Ch_result_max=L_unzip[0]#中文名
	xasis_fieldname_result_max=L_unzip[1]#英文名
	offset_degree_result_max=L_unzip[2]#偏离程度
	regression_coefficient_max=L_unzip[3]#回归系数（权重）

	# '''
	#判断字段的顺序（对筛选后的三个字段再根据字段再表结构中的顺序进行排序）
	ana_result_score={}
	ana_result_score=zhuanlu.PRO_BOF_HIS_ALLFIELDS_SCORE
	En_to_Ch_result_score=[]
	for i in range(len(xasis_fieldname_result_max)):
		En_to_Ch_result_score.append(ana_result_score[xasis_fieldname_result_max[i]][1])
	# print('表结构中字段的顺序',En_to_Ch_result_score)

	#zip压缩：中文名、英文名、偏离程度、字段顺序编号
	L_zip = list(zip(En_to_Ch_result_max,xasis_fieldname_result_max,offset_degree_result_max,En_to_Ch_result_score,regression_coefficient_max))
	#按照字段顺序进行排序（从小到大）
	L_zip.sort(key=lambda x:x[3])
	print('追溯结果的三个字段',L_zip)
	#解压缩
	L_unzip=list(zip(*L_zip))

	En_to_Ch_result_max=L_unzip[0]#中文名
	xasis_fieldname_result_max=L_unzip[1]#英文名
	offset_degree_result_max=L_unzip[2]#偏离程度
	En_to_Ch_result_score_max=L_unzip[3]#字段序号
	regression_coefficient_max=L_unzip[4]#回归系数（权重）
	# '''

	offset_degree_result_max_final=["%.2f%%"%(abs(float(n))*100) for n in list(offset_degree_result_max)]#将偏离程度值转化为保留两位小数的百分数
	#简单定性判断偏离程度（偏高、偏低）
	pos_float=[ float(n) for n in list(offset_degree_result_max)]
	offset_result_nature=qualitative_offset(pos_float)

	print('分析字段：',field)
	# print('分析字段偏离程度')
	# print(offset_value_single[0])
	# print('按操作排序后回归系数中文名')
	# print(En_to_Ch_result_score)
	# print("分析字段偏离程度定性判断")
	# print(offset_result_nature)
	# print('按操作排序后字段偏离程度')
	# print(offset_value_single_cof)
	return En_to_Ch_result_max,offset_result_nature,offset_degree_result_max_final,regression_coefficient_max








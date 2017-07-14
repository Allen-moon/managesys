import os
import sys
from datetime import datetime

from django.db import models,connection,connections
from . import util

# for slug, get_absolute_url
from django.template.defaultfilters import slugify
from django.core.urlresolvers import reverse

# delete md_file before delete/change model
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.core.files.base import ContentFile

import markdown2
from unidecode import unidecode
from taggit.managers import TaggableManager


upload_dir = 'content/ContentPost/%s/%s'

class BaseManage(models.Manager):
	#根据传入属性dict生成增删改查的sql，使用raw方法进行查询，针对绑定了model的情况
	#如果没有绑定model，也可以使用direct_xxxx_query_sqlVO传入得到的sqlVO进行查询
	def raw_query_sqlVO(self,sqlVO):
		return self.raw(sqlVO.get('sql'),sqlVO.get('vars'))

	def add_rows(self,attrs,model):
		sqlVO= util.create_insert_sql(model,attrs)
		return self.raw_query_sqlVO(sqlVO)
	def select_rows(self,attrs,model):
		sqlVO= util.create_insert_sqlVO(model,attrs)
		return  self.raw_query_sqlVO(sqlVO)
	def update_rows(self,attrs,model):
		sqlVO= util.create_update_sqlVO(model,attrs)
		return self.raw_query_sqlVO(sqlVO)
	def delete_rows(self,attrs,model):
		sqlVO= util.create_delete_sqlVO(model,attrs)
		return self.raw_query_sqlVO(sqlVO)
	'''
	queries that don’t map cleanly to models, or directly execute UPDATE, INSERT, or DELETE queries.
	'''
	#将结果返回为dict
	def dictfetchall(self,cursor):
		columns = [col[0] for col in cursor.description]
		print(columns)
		return [
	        dict(zip(columns, row))
	        for row in cursor.fetchall()
    	]

	def direct_select_query_sqlVO(self,sqlVO):
		#如果是多数据库
		#cursor = connections['my_db_alias'].cursor()
		db_name=sqlVO.get('db_name')
		print(db_name)
		if sqlVO.get('db_name')!=None:
			cursor = connections[db_name].cursor()
		else:
			cursor = connection.cursor()
		cursor.execute(sqlVO.get('sql'),sqlVO.get('vars',None))
		print(cursor)
		return self.dictfetchall(cursor)

	def direct_execute_query_sqlVO(self,sqlVO):
		db_name=sqlVO.get('db_name')
		if sqlVO.get('db_name')!=None:
			cursor = connections[db_name].cursor()
		else:
			cursor = connection.cursor()
		try:
			print('SQL [%s]' % sqlVO.get('sql'))
			cursor.execute(sqlVO.get('sql'),sqlVO.get('vars'))
		except:
			print( 'Failed to execute SQL[%s]\n' % sqlVO.get('sql') )

	def direct_get_description(self,sqlVO):
		db_name=sqlVO.get('db_name')
		if sqlVO.get('db_name')!=None:
			cursor = connections[db_name].cursor()
		else:
			cursor = connection.cursor()
		cursor.execute(sqlVO.get('sql'),sqlVO.get('vars',None))
		columns = [col[0] for col in cursor.description]
		types=[col[1].__name__ for col in cursor.description]
		columns_type=dict(zip(columns, types))
		return [columns,columns_type]

	def direct_select_query_orignal_sqlVO(self,sqlVO):
		#如果是多数据库
		#cursor = connections['my_db_alias'].cursor()
		db_name=sqlVO.get('db_name')
		print(db_name)
		if sqlVO.get('db_name')!=None:
			cursor = connections[db_name].cursor()
		else:
			cursor = connection.cursor()
		try:
			print('SQL [%s]' % sqlVO.get('sql'))
			cursor.execute(sqlVO.get('sql'),sqlVO.get('vars',None))
			return cursor.fetchall()
		except:
			print( 'Failed to execute SQL[%s]\n' % sqlVO.get('sql') )
			return False

# Create your models here.
class TransRelationManage(BaseManage):
	def get_all_tr(self):
		return self.all()


class  CONVERTERManage(BaseManage):
	def get_all_tr(self):
		return self.all()

class OrderItemManage(BaseManage):
	def get_all_tr(self):
		return self.all()



class ContentPost(models.Model):

    class Meta:
        ordering = ['-pub_date']    # ordered by pub_date descending when retriving

    def get_upload_md_name(self, filename):
        if self.pub_date:
            year = self.pub_date.year   # always store in pub_year folder
        else:
            year = datetime.now().year
        upload_to = upload_dir % (year, self.title + '.md')
        return upload_to

    def get_html_name(self, filename):
        if self.pub_date:
            year = self.pub_date.year
        else:
            year = datetime.now().year
        upload_to = upload_dir % (year, filename)
        return upload_to

    CATEGORY_CHOICES = (
        ('c', 'Common'),
        ('s', 'summary'),
        ('t', 'task'),
        ('a', 'advice'),
        ('nc', 'No Category'),
    )

    title = models.CharField(max_length=150)
    body = models.TextField(blank=True)
    md_file = models.FileField(upload_to=get_upload_md_name, blank=True)  # uploaded md file
    pub_date = models.DateTimeField('date published', auto_now_add=True)
    last_edit_date = models.DateTimeField('last edited', auto_now=True)
    slug = models.SlugField(max_length=200, blank=True)
    html_file = models.FileField(upload_to=get_html_name, blank=True)    # generated html file
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    tags = TaggableManager()

    def __str__(self):
        return self.title   # 根据继承搜索流程,先是实例属性,然后就是类属性,所以这样用没问题

    @property
    def filename(self):
        if self.md_file:
            return os.path.basename(self.title)
        else:
            return 'no md_file'

    def save(self, *args, **kwargs):
        self.slug = slugify(unidecode(self.title))
        if not self.body and self.md_file:
            self.body = self.md_file.read()

        html = markdown2.markdown(self.body,
                                  extras=["fenced-code-blocks", "tables"])
        self.html_file.save(self.title + '.html',
                            ContentFile(html.encode('utf-8')), save=False)
        self.html_file.close()

        super().save(*args, **kwargs)

    def display_html(self):
        with open(self.html_file.path, encoding='utf-8') as f:
            return f.read()

    def get_absolute_url(self):
        return reverse('data_import.views.contentpost',
                       kwargs={'slug': self.slug, 'post_id': self.id})


@receiver(pre_delete, sender=ContentPost)
def post_delete(instance, **kwargs):
    if instance.md_file:
        instance.md_file.delete(save=False)
    if instance.html_file:
        instance.html_file.delete(save=False)


class ContentPostImage(models.Model):

    def get_upload_img_name(self, filename):
        upload_to = upload_dir % ('images', filename)  # filename involves extension
        return upload_to

    contentpost = models.ForeignKey(ContentPost, related_name='images')
    image = models.ImageField(upload_to=get_upload_img_name)


class TransRelation(models.Model):
	own_uid = models.CharField(max_length=100,blank=True)#关联字段在自己设计数据库的字段名
	classification = models.CharField(max_length=100,blank=True)#分类
	real_meaning = models.CharField(max_length=100,blank=True)#物理意义
	own_table = models.CharField(max_length=100,blank=True)#自己设计的表名
	own_col = models.CharField(max_length=100,blank=True)#需要迁移字段在自己设计数据库的表中的字段名
	from_uid = models.CharField(max_length=100)#关联字段在原数据库中的字段名
	from_system = models.CharField(max_length=100,blank=True)#需要迁移字段所在的系统
	from_dept = models.CharField(max_length=100,blank=True)#需要迁移字段所在部分
	from_table = models.CharField(max_length=100,blank=True)#需要迁移字段在原数据库的表名
	from_col = models.CharField(max_length=100,blank=True)#需要迁移字段在原数据库表的列名
	remarks = models.CharField(max_length=100,blank=True)#备注
	procedure = models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

	def __unicode__(self):
		return u'{uid}{own_col}{from_col}'.format(uid=self.uid,own_col=self.own_col,from_col=self.from_col)

	objects = TransRelationManage()


class steel_price(models.Model):
	steeltype = models.CharField(max_length=100,blank=True)
	tradeno = models.CharField(max_length=100,blank=True)
	delivery = models.CharField(max_length=100,blank=True)
	specification = models.CharField(max_length=100,blank=True)
	factory = models.CharField(max_length=100,blank=True)
	price = models.CharField(max_length=100,blank=True)
	updown = models.CharField(max_length=100,blank=True)
	region = models.CharField(max_length=100,blank=True)
	trademark = models.CharField(max_length=100,blank=True)
	updatetime = models.DateTimeField(blank=True)
	remark = models.CharField(max_length=100,blank=True)
	
	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])



class MaterialCode(models.Model):
	"""docstring for Material code"""
	MATRLNO=models.CharField(max_length=100,blank=True,null=True)
	remarks=models.CharField(max_length=100,blank=True,null=True)
	INVENTORYTYPE=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])
	objects = BaseManage()

class KR(models.Model):
	heatNo=models.CharField(max_length=30,primary_key=True)
	IS_NO=models.CharField(max_length=100,blank=True,null=True)
	LADLENO=models.CharField(max_length=100,blank=True,null=True)
	POS_NR=models.CharField(max_length=100,blank=True,null=True)
	EVT_NO=models.CharField(max_length=100,blank=True,null=True)
	EVT_CODE=models.CharField(max_length=100,blank=True,null=True)
	EVT_TIME=models.CharField(max_length=100,blank=True,null=True)
	ARRIVEDATE=models.CharField(max_length=100,blank=True,null=True)
	ARRIVETIME=models.CharField(max_length=100,blank=True,null=True)
	DEPARTUREDATE=models.CharField(max_length=100,blank=True,null=True)
	DEPARTURETIME=models.CharField(max_length=100,blank=True,null=True)
	CINDERFRONTSTARTTIME=models.CharField(max_length=100,blank=True,null=True)
	CINDERFRONTENDTIME=models.CharField(max_length=100,blank=True,null=True)
	STIRBEGTIME=models.CharField(max_length=100,blank=True,null=True)
	STIRENDTIME=models.CharField(max_length=100,blank=True,null=True)
	CINDERREARENDTIME=models.CharField(max_length=100,blank=True,null=True)
	CINDERREARSTARTTIME=models.CharField(max_length=100,blank=True,null=True)
	TEMP_TIME=models.CharField(max_length=100,blank=True,null=True)
	TEMP_NO=models.CharField(max_length=100,blank=True,null=True)
	TEMP_TYPE=models.CharField(max_length=100,blank=True,null=True)
	TEMP_VALUE=models.CharField(max_length=100,blank=True,null=True)
	ARRIVETEMP=models.CharField(max_length=100,blank=True,null=True)
	LEAVETEMP=models.CharField(max_length=100,blank=True,null=True)
	STATION=models.CharField(max_length=100,blank=True,null=True)
	OPERATECREW=models.CharField(max_length=100,blank=True,null=True)
	OPERATESHIFT=models.CharField(max_length=100,blank=True,null=True)
	STEELNEXTSTATION=models.CharField(max_length=100,blank=True,null=True)
	AGITATORLIFE=models.CharField(max_length=100,blank=True,null=True)
	STATION=models.CharField(max_length=100,blank=True,null=True)
	SLAGREMOVEWGT=models.CharField(max_length=100,blank=True,null=True)
	INSULATIONAGENTWGT=models.CharField(max_length=100,blank=True,null=True)
	SLAGCONDENSERWGT=models.CharField(max_length=100,blank=True,null=True)
	CARICOMS=models.CharField(max_length=100,blank=True,null=True)
	SORBENTWGT=models.CharField(max_length=100,blank=True,null=True)
	INSERTIONDEPTH=models.CharField(max_length=100,blank=True,null=True)
	MATERIALWGT=models.CharField(max_length=100,blank=True,null=True)
	N2GASCONSUMPTION=models.CharField(max_length=100,blank=True,null=True)
	ARRIVEWGT=models.CharField(max_length=100,blank=True,null=True)
	LEAVEWGT=models.CharField(max_length=100,blank=True,null=True)
	STEELNETWGT=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])



class BOF(models.Model):
	heatNo=models.CharField(max_length=30,primary_key=True)
	MIRON_WGT=models.CharField(max_length=100,blank=True,null=True)
	COLDPIGWGT=models.CharField(max_length=100,blank=True,null=True)
	SCRAPWGT=models.CharField(max_length=100,blank=True,null=True)
	SCRAP_NUM=models.CharField(max_length=100,blank=True,null=True)
	SCRAP_CODE1=models.CharField(max_length=100,blank=True,null=True)
	SCRAP_WGT1=models.CharField(max_length=100,blank=True,null=True)
	SCRAP_CODE2=models.CharField(max_length=100,blank=True,null=True)
	SCRAP_WGT2=models.CharField(max_length=100,blank=True,null=True)
	SCRAP_CODE3=models.CharField(max_length=100,blank=True,null=True)
	SCRAP_WGT3=models.CharField(max_length=100,blank=True,null=True)
	SCRAP_CODE4=models.CharField(max_length=100,blank=True,null=True)
	SCRAP_WGT4=models.CharField(max_length=100,blank=True,null=True)
	SCRAP_CODE5=models.CharField(max_length=100,blank=True,null=True)
	SCRAP_WGT5=models.CharField(max_length=100,blank=True,null=True)
	SCRAP_CODE6=models.CharField(max_length=100,blank=True,null=True)
	SCRAP_WGT6=models.CharField(max_length=100,blank=True,null=True)
	SCRAP_CODE7=models.CharField(max_length=100,blank=True,null=True)
	SCRAP_WGT7=models.CharField(max_length=100,blank=True,null=True)
	SCRAP_WGT8=models.CharField(max_length=100,blank=True,null=True)
	INSULATIONAGENT=models.CharField(max_length=100,blank=True,null=True)
	HEAT_WGT=models.CharField(max_length=100,blank=True,null=True)
	FIRSTCATCHOXYGENCONSUME=models.CharField(max_length=100,blank=True,null=True)
	TOTALOXYGENCONSUME=models.CharField(max_length=100,blank=True,null=True)
	N2CONSUME=models.CharField(max_length=100,blank=True,null=True)
	STEELWGT=models.CharField(max_length=100,blank=True,null=True)
	SLAGWGT=models.CharField(max_length=100,blank=True,null=True)
	MSG_DATE_Scrap=models.CharField(max_length=100,blank=True,null=True)
	MSG_DATE_Miron=models.CharField(max_length=100,blank=True,null=True)
	MSG_DATE_Pool=models.CharField(max_length=100,blank=True,null=True)
	MSG_DATE_Plan=models.CharField(max_length=100,blank=True,null=True)
	planSpec=models.CharField(max_length=100,blank=True,null=True)
	MIRON_TEMP=models.CharField(max_length=100,blank=True,null=True)
	MIRON_C=models.CharField(max_length=100,blank=True,null=True)
	MIRON_SI=models.CharField(max_length=100,blank=True,null=True)
	MIRON_MN=models.CharField(max_length=100,blank=True,null=True)
	MIRON_P=models.CharField(max_length=100,blank=True,null=True)
	MIRON_S=models.CharField(max_length=100,blank=True,null=True)
	IS_TEMP=models.CharField(max_length=100,blank=True,null=True)
	BEFARTEMP=models.CharField(max_length=100,blank=True,null=True)
	CARBONTEMPERATURE=models.CharField(max_length=100,blank=True,null=True)
	TEMP_TIME=models.CharField(max_length=100,blank=True,null=True)
	TEMP_NO=models.CharField(max_length=100,blank=True,null=True)
	TEMP_VALUE=models.CharField(max_length=100,blank=True,null=True)
	FIRSTCATCHCARBONC=models.CharField(max_length=100,blank=True,null=True)
	FIRSTCATCHCARBONP=models.CharField(max_length=100,blank=True,null=True)
	MSG_DATE=models.CharField(max_length=100,blank=True,null=True)
	SAMPLEID=models.CharField(max_length=100,blank=True,null=True)
	SAMPLE_LOCATION =models.CharField(max_length=100,blank=True,null=True)
	VALUE_C=models.CharField(max_length=100,blank=True,null=True)
	VALUE_SI=models.CharField(max_length=100,blank=True,null=True)
	VALUE_MN=models.CharField(max_length=100,blank=True,null=True)
	VALUE_P=models.CharField(max_length=100,blank=True,null=True)
	VALUE_S=models.CharField(max_length=100,blank=True,null=True)
	STATION=models.CharField(max_length=100,blank=True,null=True)
	EVT_NO=models.CharField(max_length=100,blank=True,null=True)
	EVT_CODE=models.CharField(max_length=100,blank=True,null=True)
	EVT_TIME=models.CharField(max_length=100,blank=True,null=True)
	TAPPINGSTARTDATE=models.CharField(max_length=100,blank=True,null=True)
	TAPPINGSTARTTIME=models.CharField(max_length=100,blank=True,null=True)
	TAPPINGENDDATE=models.CharField(max_length=100,blank=True,null=True)
	TAPPINGENDTIME=models.CharField(max_length=100,blank=True,null=True)
	TIMEOFSLAGSPLISHING=models.CharField(max_length=100,blank=True,null=True)
	PUTSPRAYGUNTIME=models.CharField(max_length=100,blank=True,null=True)
	BOSTRT_TIME=models.CharField(max_length=100,blank=True,null=True)
	BOEND_TIME=models.CharField(max_length=100,blank=True,null=True)
	BO_DUR=models.CharField(max_length=100,blank=True,null=True)
	TIMEOFOXYGEN=models.CharField(max_length=100,blank=True,null=True)
	TOTALTIMEOFOXYGEN=models.CharField(max_length=100,blank=True,null=True)
	PERIOD=models.CharField(max_length=100,blank=True,null=True)
	SUBLANCE_INDEPTH=models.CharField(max_length=100,blank=True,null=True)
	LEQHEIGH=models.CharField(max_length=100,blank=True,null=True)
	BOTTOMBLOWING=models.CharField(max_length=100,blank=True,null=True)


	objects = CONVERTERManage()

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])




class Sales(models.Model):
	orderNo=models.CharField(max_length=100,blank=True)#订单编号
	orderItem=models.CharField(max_length=100,null=True)#订单项次
	dispListNo=models.CharField(max_length=100,null=True)#发货通知单号
	tradeNo=models.CharField(max_length=100,null=True)#牌号
	orderItemWeight=models.CharField(max_length=100,null=True)#订单项次重量
	orderPrice=models.CharField(max_length=100,null=True)#订单项次单价

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])


	objects = OrderItemManage()

class external_eles(models.Model):
	shipping_price =models.FloatField(blank=True)#海运费
	scrap =models.FloatField(blank=True)#废钢
	cooking_coal=models.FloatField(blank=True)#炼焦煤
	iron_powder=models.FloatField(blank=True)#铁精粉
	now_ore=models.FloatField(blank=True)#现矿
	import_ore=models.FloatField(blank=True)#进口矿
	now_date = models.DateField()#CREATEDATE CY

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])




class TransRelationMultikey(models.Model):
	own_uid1 = models.CharField(max_length=100,blank=True)#关联字段在自己设计数据库的字段名
	own_uid2 = models.CharField(max_length=100,blank=True)#关联字段在自己设计数据库的字段名
	classification = models.CharField(max_length=100,blank=True)#分类
	real_meaning = models.CharField(max_length=100,blank=True)#物理意义
	own_table = models.CharField(max_length=100,blank=True)#自己设计的表名
	own_col = models.CharField(max_length=100,blank=True)#需要迁移字段在自己设计数据库的表中的字段名
	from_uid1 = models.CharField(max_length=100)#关联字段在原数据库中的字段名
	from_uid2 = models.CharField(max_length=100)#关联字段在原数据库中的字段名
	from_system = models.CharField(max_length=100,blank=True)#需要迁移字段所在的系统
	from_dept = models.CharField(max_length=100,blank=True)#需要迁移字段所在部分
	from_table = models.CharField(max_length=100,blank=True)#需要迁移字段在原数据库的表名
	from_col = models.CharField(max_length=100,blank=True)#需要迁移字段在原数据库表的列名
	remarks = models.CharField(max_length=100,blank=False)#备注
	procedure = models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])
	objects = BaseManage()

class Custarea(models.Model):
	custNo =models.CharField(max_length=100,primary_key=True)#客户编号
	recName=models.CharField(max_length=100,blank=True,null=True)#客户中文名称
	province=models.CharField(max_length=100,blank=True,null=True)#客户所在省
	city=models.CharField(max_length=100,blank=True,null=True)#客户所在市
	country=models.CharField(max_length=100,blank=True,null=True)#客户所在国家

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

'''
mes数据模型
'''
#炼钢
class LG_HEATNO(models.Model):
	heatNo=models.CharField(max_length=30,primary_key=True)
	putSprayGunTime=models.CharField(max_length=100,blank=True,null=True)
	endTemperature=models.CharField(max_length=100,blank=True,null=True)
	bathCarbon=models.CharField(max_length=100,blank=True,null=True)
	bathOxygen=models.CharField(max_length=100,blank=True,null=True)
	arriveDate=models.CharField(max_length=100,blank=True,null=True)
	arriveTime=models.CharField(max_length=100,blank=True,null=True)
	timeOfSupplyM=models.CharField(max_length=100,blank=True,null=True)
	timeOfSupplyS=models.CharField(max_length=100,blank=True,null=True)
	steelWgt=models.CharField(max_length=100,blank=True,null=True)
	ladleNo=models.CharField(max_length=100,blank=True,null=True)
	operateCrew=models.CharField(max_length=100,blank=True,null=True)
	operateShift=models.CharField(max_length=100,blank=True,null=True)
	operateDate=models.CharField(max_length=100,blank=True,null=True)
	scrapSteel=models.CharField(max_length=100,blank=True,null=True)
	moldFlowA=models.CharField(max_length=100,blank=True,null=True)
	moldFlowB=models.CharField(max_length=100,blank=True,null=True)
	moldFlowC=models.CharField(max_length=100,blank=True,null=True)
	moldFlowD=models.CharField(max_length=100,blank=True,null=True)
	moldFlowE=models.CharField(max_length=100,blank=True,null=True)
	moldFlowF=models.CharField(max_length=100,blank=True,null=True)
	minWgtInTundish=models.CharField(max_length=100,blank=True,null=True)
	speedMinValueA=models.CharField(max_length=100,blank=True,null=True)
	speedMinValueB=models.CharField(max_length=100,blank=True,null=True)
	speedMinValueC=models.CharField(max_length=100,blank=True,null=True)
	speedMinValueD=models.CharField(max_length=100,blank=True,null=True)
	speedMinValueE=models.CharField(max_length=100,blank=True,null=True)
	speedMinValueF=models.CharField(max_length=100,blank=True,null=True)
	casting=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])


class LG_SLABID(models.Model):
	slabId=models.CharField(max_length=30,primary_key=True)
	warehouseNo=models.CharField(max_length=100,blank=True,null=True)
	areaNo=models.CharField(max_length=100,blank=True,null=True)
	length=models.CharField(max_length=100,blank=True,null=True)
	weight=models.CharField(max_length=100,blank=True,null=True)
	qty=models.CharField(max_length=100,blank=True,null=True)
	heatNo=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])


class LG_HEATORDER(models.Model):
	HEATORDER=models.CharField(max_length=30,primary_key=True)
	heatNo=models.CharField(max_length=100,blank=True,null=True)
	sectionType=models.CharField(max_length=100,blank=True,null=True)
	billetType=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])


#高炉
class BF_LADLENO(models.Model):
	ladleNo=models.CharField(max_length=30,primary_key=True)
	deptNo=models.CharField(max_length=100,blank=True,null=True)
	ladleName=models.CharField(max_length=100,blank=True,null=True)
	bfNo=models.CharField(max_length=100,blank=True,null=True)
	bfTappingNo=models.CharField(max_length=100,blank=True,null=True)
	ladleLot=models.CharField(max_length=100,blank=True,null=True)
	ladleSeq=models.CharField(max_length=100,blank=True,null=True)
	useDate=models.CharField(max_length=100,blank=True,null=True)
	disuseDate=models.CharField(max_length=100,blank=True,null=True)
	locationId=models.CharField(max_length=100,blank=True,null=True)
	status=models.CharField(max_length=100,blank=True,null=True)
	minWgt=models.CharField(max_length=100,blank=True,null=True)
	maxWgt=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])


class BF_SAMPLEID(models.Model):
	sampleId=models.CharField(max_length=30,primary_key=True)
	formId=models.CharField(max_length=100,blank=True,null=True)
	sendDate=models.CharField(max_length=100,blank=True,null=True)
	sendTime=models.CharField(max_length=100,blank=True,null=True)
	receiveDate=models.CharField(max_length=100,blank=True,null=True)
	receiveTime=models.CharField(max_length=100,blank=True,null=True)
	accountDate=models.CharField(max_length=100,blank=True,null=True)
	sampleType=models.CharField(max_length=100,blank=True,null=True)
	equipNo=models.CharField(max_length=100,blank=True,null=True)
	mtrlNo=models.CharField(max_length=100,blank=True,null=True)
	testShift=models.CharField(max_length=100,blank=True,null=True)
	testCrew=models.CharField(max_length=100,blank=True,null=True)
	bfTappingNo=models.CharField(max_length=100,blank=True,null=True)
	ladleNo=models.CharField(max_length=100,blank=True,null=True)
	testApplyNo=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])


class BF_TESTAPPLYNO(models.Model):
	testApplyNo=models.CharField(max_length=30,primary_key=True)
	sampleLocation=models.CharField(max_length=100,blank=True,null=True)
	sampleDate=models.CharField(max_length=100,blank=True,null=True)
	sampleTime=models.CharField(max_length=100,blank=True,null=True)
	sampleCrew=models.CharField(max_length=100,blank=True,null=True)
	sampleShift=models.CharField(max_length=100,blank=True,null=True)
	sampleType=models.CharField(max_length=100,blank=True,null=True)
	tappingHole=models.CharField(max_length=100,blank=True,null=True)
	sampleMtrlNo=models.CharField(max_length=100,blank=True,null=True)
	sampleBatchNo=models.CharField(max_length=100,blank=True,null=True)
	sampleEmpNo=models.CharField(max_length=100,blank=True,null=True)
	resampleNo=models.CharField(max_length=100,blank=True,null=True)
	bfTappingNo=models.CharField(max_length=100,blank=True,null=True)
	ladleNo=models.CharField(max_length=100,blank=True,null=True)
	laboratory=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

#轧钢
class SR_SECTIONTYPE(models.Model):
	sectionType=models.CharField(max_length=30,primary_key=True)
	dimensionA=models.CharField(max_length=100,blank=True,null=True)
	dimensionB=models.CharField(max_length=100,blank=True,null=True)
	dimensionC=models.CharField(max_length=100,blank=True,null=True)
	dimensionAStr=models.CharField(max_length=100,blank=True,null=True)
	dimensionBStr=models.CharField(max_length=100,blank=True,null=True)
	dimensionCStr=models.CharField(max_length=100,blank=True,null=True)
	sectionMemo=models.CharField(max_length=100,blank=True,null=True)
	measureType=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SR_INVID(models.Model):
	invId=models.CharField(max_length=30,primary_key=True)
	grade=models.CharField(max_length=100,blank=True,null=True)
	MscNo=models.CharField(max_length=100,blank=True,null=True)
	suDisp=models.CharField(max_length=100,blank=True,null=True)
	teDisp=models.CharField(max_length=100,blank=True,null=True)
	MscLineNo=models.CharField(max_length=100,blank=True,null=True)
	sourceType=models.CharField(max_length=100,blank=True,null=True)
	custNo=models.CharField(max_length=100,blank=True,null=True)
	spec=models.CharField(max_length=100,blank=True,null=True)
	sectionType=models.CharField(max_length=100,blank=True,null=True)
	orderItem=models.CharField(max_length=100,blank=True,null=True)
	orderNo=models.CharField(max_length=100,blank=True,null=True)
	prodType=models.CharField(max_length=100,blank=True,null=True)
	prodLine=models.CharField(max_length=100,blank=True,null=True)
	prodTypeNo=models.CharField(max_length=100,blank=True,null=True)
	prodClass=models.CharField(max_length=100,blank=True,null=True)
	prodDetailClassNo=models.CharField(max_length=100,blank=True,null=True)
	spFldD=models.CharField(max_length=100,blank=True,null=True)
	tradeNo=models.CharField(max_length=100,blank=True,null=True)
	isInStock=models.CharField(max_length=100,blank=True,null=True)
	isLoad=models.CharField(max_length=100,blank=True,null=True)
	isOwner=models.CharField(max_length=100,blank=True,null=True)
	lastSuDisp=models.CharField(max_length=100,blank=True,null=True)
	lastTeDisp=models.CharField(max_length=100,blank=True,null=True)
	dimensionA=models.CharField(max_length=100,blank=True,null=True)
	dimensionB=models.CharField(max_length=100,blank=True,null=True)
	length=models.CharField(max_length=100,blank=True,null=True)
	measureType=models.CharField(max_length=100,blank=True,null=True)
	pcs1=models.CharField(max_length=100,blank=True,null=True)
	weight1=models.CharField(max_length=100,blank=True,null=True)
	weightWgt=models.CharField(max_length=100,blank=True,null=True)
	thryWgt1=models.CharField(max_length=100,blank=True,null=True)
	status1=models.CharField(max_length=100,blank=True,null=True)
	warehouseNo2=models.CharField(max_length=100,blank=True,null=True)
	areaNo1=models.CharField(max_length=100,blank=True,null=True)
	qty=models.CharField(max_length=100,blank=True,null=True)
	heatNo=models.CharField(max_length=100,blank=True,null=True)
	tradeNo1=models.CharField(max_length=100,blank=True,null=True)
	prodLine2=models.CharField(max_length=100,blank=True,null=True)
	activityId=models.CharField(max_length=100,blank=True,null=True)
	acctDate=models.CharField(max_length=100,blank=True,null=True)
	dimensionA1=models.CharField(max_length=100,blank=True,null=True)
	dimensionB1=models.CharField(max_length=100,blank=True,null=True)
	length1=models.CharField(max_length=100,blank=True,null=True)
	prodDate1=models.CharField(max_length=100,blank=True,null=True)
	pcs2=models.CharField(max_length=100,blank=True,null=True)
	weight=models.CharField(max_length=100,blank=True,null=True)
	thryWgt=models.CharField(max_length=100,blank=True,null=True)
	warehouseNo1=models.CharField(max_length=100,blank=True,null=True)
	seqNo=models.CharField(max_length=100,blank=True,null=True)
	invWgt=models.CharField(max_length=100,blank=True,null=True)
	dimensionA4=models.CharField(max_length=100,blank=True,null=True)
	dimensionB4=models.CharField(max_length=100,blank=True,null=True)
	prodOperateDate=models.CharField(max_length=100,blank=True,null=True)
	prodCrew=models.CharField(max_length=100,blank=True,null=True)
	sectionType1=models.CharField(max_length=100,blank=True,null=True)
	weightDate=models.CharField(max_length=100,blank=True,null=True)
	weightTime=models.CharField(max_length=100,blank=True,null=True)
	length2=models.CharField(max_length=100,blank=True,null=True)
	prodShift=models.CharField(max_length=100,blank=True,null=True)
	prodOperateEmpl=models.CharField(max_length=100,blank=True,null=True)
	prodOperateTime=models.CharField(max_length=100,blank=True,null=True)
	prodDate=models.CharField(max_length=100,blank=True,null=True)
	prodTime=models.CharField(max_length=100,blank=True,null=True)
	invPcs=models.CharField(max_length=100,blank=True,null=True)
	recordDate=models.CharField(max_length=100,blank=True,null=True)
	operateCrew=models.CharField(max_length=100,blank=True,null=True)
	operateDate1=models.CharField(max_length=100,blank=True,null=True)
	operateShift=models.CharField(max_length=100,blank=True,null=True)
	operator1=models.CharField(max_length=100,blank=True,null=True)
	recordEmpl=models.CharField(max_length=100,blank=True,null=True)
	recordTime=models.CharField(max_length=100,blank=True,null=True)
	rollNo=models.CharField(max_length=100,blank=True,null=True)
	tradeNo2=models.CharField(max_length=100,blank=True,null=True)
	logSeq1=models.CharField(max_length=100,blank=True,null=True)
	dimensionA2=models.CharField(max_length=100,blank=True,null=True)
	dimensionB2=models.CharField(max_length=100,blank=True,null=True)
	length3=models.CharField(max_length=100,blank=True,null=True)
	prodClass1=models.CharField(max_length=100,blank=True,null=True)
	prodLine3=models.CharField(max_length=100,blank=True,null=True)
	prodType1=models.CharField(max_length=100,blank=True,null=True)
	sectionType2=models.CharField(max_length=100,blank=True,null=True)
	prodTypeNo1=models.CharField(max_length=100,blank=True,null=True)
	accDate=models.CharField(max_length=100,blank=True,null=True)
	measureType1=models.CharField(max_length=100,blank=True,null=True)
	moveType=models.CharField(max_length=100,blank=True,null=True)
	isInStock1=models.CharField(max_length=100,blank=True,null=True)
	chgType=models.CharField(max_length=100,blank=True,null=True)
	pcs3=models.CharField(max_length=100,blank=True,null=True)
	logSeq3=models.CharField(max_length=100,blank=True,null=True)
	errCode=models.CharField(max_length=2000,blank=True,null=True)
	isRls=models.CharField(max_length=100,blank=True,null=True)
	appId=models.CharField(max_length=100,blank=True,null=True)
	tradeNo3=models.CharField(max_length=100,blank=True,null=True)
	logSeq=models.CharField(max_length=100,blank=True,null=True)
	dimensionA5=models.CharField(max_length=100,blank=True,null=True)
	dimensionB5=models.CharField(max_length=100,blank=True,null=True)
	length4=models.CharField(max_length=100,blank=True,null=True)
	preSuDisp=models.CharField(max_length=100,blank=True,null=True)
	suDisp1=models.CharField(max_length=100,blank=True,null=True)
	preProdClass=models.CharField(max_length=100,blank=True,null=True)
	prodClass2=models.CharField(max_length=100,blank=True,null=True)
	preProdLine=models.CharField(max_length=100,blank=True,null=True)
	prodLine1=models.CharField(max_length=100,blank=True,null=True)
	preProdType=models.CharField(max_length=100,blank=True,null=True)
	prodType2=models.CharField(max_length=100,blank=True,null=True)
	preSectionType=models.CharField(max_length=100,blank=True,null=True)
	sectionType3=models.CharField(max_length=100,blank=True,null=True)
	preGrade=models.CharField(max_length=100,blank=True,null=True)
	grade1=models.CharField(max_length=100,blank=True,null=True)
	preProdTypeNo=models.CharField(max_length=100,blank=True,null=True)
	prodTypeNo2=models.CharField(max_length=100,blank=True,null=True)
	preMscLineNo=models.CharField(max_length=100,blank=True,null=True)
	MscLineNo1=models.CharField(max_length=100,blank=True,null=True)
	preMscNo=models.CharField(max_length=100,blank=True,null=True)
	MscNo1=models.CharField(max_length=100,blank=True,null=True)
	userType=models.CharField(max_length=100,blank=True,null=True)
	preTeDisp=models.CharField(max_length=100,blank=True,null=True)
	teDisp1=models.CharField(max_length=100,blank=True,null=True)
	operator=models.CharField(max_length=100,blank=True,null=True)
	operateDate=models.CharField(max_length=100,blank=True,null=True)
	ipCode=models.CharField(max_length=100,blank=True,null=True)
	command=models.CharField(max_length=100,blank=True,null=True)
	pcs=models.CharField(max_length=100,blank=True,null=True)
	Prepcs=models.CharField(max_length=100,blank=True,null=True)
	ordNo=models.CharField(max_length=100,blank=True,null=True)
	preOrdNo=models.CharField(max_length=100,blank=True,null=True)
	ordItem=models.CharField(max_length=100,blank=True,null=True)
	preOrdItem=models.CharField(max_length=100,blank=True,null=True)
	status=models.CharField(max_length=100,blank=True,null=True)
	preStatus=models.CharField(max_length=100,blank=True,null=True)
	warehouseNo=models.CharField(max_length=100,blank=True,null=True)
	preWarehouseNo=models.CharField(max_length=100,blank=True,null=True)
	areaNo=models.CharField(max_length=100,blank=True,null=True)
	preAreaNo=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SR_ROLLNO(models.Model):
	rollNo=models.CharField(max_length=30,primary_key=True)
	schdDate=models.CharField(max_length=100,blank=True,null=True)
	schdSeq=models.CharField(max_length=100,blank=True,null=True)
	boundQty=models.CharField(max_length=100,blank=True,null=True)
	CValue=models.CharField(max_length=100,blank=True,null=True)
	MnValue=models.CharField(max_length=100,blank=True,null=True)
	orderNo=models.CharField(max_length=100,blank=True,null=True)
	priceWgt=models.CharField(max_length=100,blank=True,null=True)
	ageingPeriod=models.CharField(max_length=100,blank=True,null=True)
	skipDate=models.CharField(max_length=100,blank=True,null=True)
	skipOperateDate=models.CharField(max_length=100,blank=True,null=True)
	prodLineNo1=models.CharField(max_length=100,blank=True,null=True)
	heatNo1=models.CharField(max_length=100,blank=True,null=True)
	warehouseNo1=models.CharField(max_length=100,blank=True,null=True)
	areaNo1=models.CharField(max_length=100,blank=True,null=True)
	rowNo1=models.CharField(max_length=100,blank=True,null=True)
	columnNo1=models.CharField(max_length=100,blank=True,null=True)
	layer1=models.CharField(max_length=100,blank=True,null=True)
	billetLength1=models.CharField(max_length=100,blank=True,null=True)
	billetDimensionA=models.CharField(max_length=100,blank=True,null=True)
	billetDimensionB=models.CharField(max_length=100,blank=True,null=True)
	sectionType1=models.CharField(max_length=100,blank=True,null=True)
	skipCrew=models.CharField(max_length=100,blank=True,null=True)
	skipShift=models.CharField(max_length=100,blank=True,null=True)
	skipOperateEmpl=models.CharField(max_length=100,blank=True,null=True)
	skipTime=models.CharField(max_length=100,blank=True,null=True)
	skipOperateTime=models.CharField(max_length=100,blank=True,null=True)
	skipWgt=models.CharField(max_length=100,blank=True,null=True)
	gkNo=models.CharField(max_length=100,blank=True,null=True)
	seqNo=models.CharField(max_length=100,blank=True,null=True)
	cobbleDate=models.CharField(max_length=100,blank=True,null=True)
	cobbleOperateDate=models.CharField(max_length=100,blank=True,null=True)
	cobbleWgt=models.CharField(max_length=100,blank=True,null=True)
	gkNo2=models.CharField(max_length=100,blank=True,null=True)
	heatNo2=models.CharField(max_length=100,blank=True,null=True)
	prodLineNo2=models.CharField(max_length=100,blank=True,null=True)
	sectionType2=models.CharField(max_length=100,blank=True,null=True)
	dutyDepart=models.CharField(max_length=100,blank=True,null=True)
	billetDimensionA2=models.CharField(max_length=100,blank=True,null=True)
	billetDimensionB2=models.CharField(max_length=100,blank=True,null=True)
	billetLength2=models.CharField(max_length=100,blank=True,null=True)
	cobbleCrew=models.CharField(max_length=100,blank=True,null=True)
	cobbleShift=models.CharField(max_length=100,blank=True,null=True)
	cobbleOperateEmpl=models.CharField(max_length=100,blank=True,null=True)
	cobbleTime=models.CharField(max_length=100,blank=True,null=True)
	cobbleOperateTime=models.CharField(max_length=100,blank=True,null=True)
	cobblePcs=models.CharField(max_length=100,blank=True,null=True)
	warehouseNo2=models.CharField(max_length=100,blank=True,null=True)
	areaNo2=models.CharField(max_length=100,blank=True,null=True)
	rowNo2=models.CharField(max_length=100,blank=True,null=True)
	columnNo2=models.CharField(max_length=100,blank=True,null=True)
	layer2=models.CharField(max_length=100,blank=True,null=True)
	seqNo1=models.CharField(max_length=100,blank=True,null=True)
	warehouseNo3=models.CharField(max_length=100,blank=True,null=True)
	areaNo3=models.CharField(max_length=100,blank=True,null=True)
	gkNo3=models.CharField(max_length=100,blank=True,null=True)
	seqNo2=models.CharField(max_length=100,blank=True,null=True)
	stopDateB=models.CharField(max_length=100,blank=True,null=True)
	stopTimeB=models.CharField(max_length=100,blank=True,null=True)
	stopDateE=models.CharField(max_length=100,blank=True,null=True)
	stopTimeE=models.CharField(max_length=100,blank=True,null=True)
	stopTime=models.CharField(max_length=100,blank=True,null=True)
	stopCrew=models.CharField(max_length=100,blank=True,null=True)
	stopShift=models.CharField(max_length=100,blank=True,null=True)
	stopDept=models.CharField(max_length=100,blank=True,null=True)
	stopReason=models.CharField(max_length=100,blank=True,null=True)
	samplingIdMan=models.CharField(max_length=100,blank=True,null=True)
	entrustOrderNo=models.CharField(max_length=100,blank=True,null=True)
	entrustEmpl=models.CharField(max_length=100,blank=True,null=True)
	prodLineNo=models.CharField(max_length=100,blank=True,null=True)
	orderItem=models.CharField(max_length=100,blank=True,null=True)
	entrustDate=models.CharField(max_length=100,blank=True,null=True)
	entrustTime=models.CharField(max_length=100,blank=True,null=True)
	sampSeqNo=models.CharField(max_length=100,blank=True,null=True)
	indexId=models.CharField(max_length=100,blank=True,null=True)
	logDate=models.CharField(max_length=100,blank=True,null=True)
	logTime=models.CharField(max_length=100,blank=True,null=True)
	sectionType=models.CharField(max_length=100,blank=True,null=True)
	stdProdCode=models.CharField(max_length=100,blank=True,null=True)
	testItem=models.CharField(max_length=200,blank=True,null=True)
	invId=models.CharField(max_length=100,blank=True,null=True)
	inputCode=models.CharField(max_length=100,blank=True,null=True)
	prodShift=models.CharField(max_length=100,blank=True,null=True)
	prodCrew=models.CharField(max_length=100,blank=True,null=True)
	prodDate=models.CharField(max_length=100,blank=True,null=True)
	prodDiameter=models.CharField(max_length=100,blank=True,null=True)
	dimensionB5=models.CharField(max_length=100,blank=True,null=True)
	prodLength5=models.CharField(max_length=100,blank=True,null=True)
	prodWgt=models.CharField(max_length=100,blank=True,null=True)
	prodQty=models.CharField(max_length=100,blank=True,null=True)
	weightOperater=models.CharField(max_length=100,blank=True,null=True)
	weightDate=models.CharField(max_length=100,blank=True,null=True)
	weightTime=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SR_SCHDNO(models.Model):
	schdNo=models.CharField(max_length=30,primary_key=True)
	produceShift=models.CharField(max_length=100,blank=True,null=True)
	produceCrew=models.CharField(max_length=100,blank=True,null=True)
	rollBegDate=models.CharField(max_length=100,blank=True,null=True)
	rollBegTime=models.CharField(max_length=100,blank=True,null=True)
	rollEndDate=models.CharField(max_length=100,blank=True,null=True)
	rollEndTime=models.CharField(max_length=100,blank=True,null=True)
	schdDate=models.CharField(max_length=100,blank=True,null=True)
	schdSeq=models.CharField(max_length=100,blank=True,null=True)
	status=models.CharField(max_length=100,blank=True,null=True)
	schdDemandWgt=models.CharField(max_length=100,blank=True,null=True)
	schdWgt=models.CharField(max_length=100,blank=True,null=True)
	orderNo=models.CharField(max_length=100,blank=True,null=True)
	orderItem=models.CharField(max_length=100,blank=True,null=True)
	shipedDate=models.CharField(max_length=100,blank=True,null=True)
	custNo=models.CharField(max_length=100,blank=True,null=True)
	orderTradeNo=models.CharField(max_length=100,blank=True,null=True)
	pcsOfBdl=models.CharField(max_length=100,blank=True,null=True)
	orderNo1=models.CharField(max_length=100,blank=True,null=True)
	orderItem1=models.CharField(max_length=100,blank=True,null=True)
	orderDimensionA=models.CharField(max_length=100,blank=True,null=True)
	orderDimensionB=models.CharField(max_length=100,blank=True,null=True)
	orderLength=models.CharField(max_length=100,blank=True,null=True)
	seqNo=models.CharField(max_length=100,blank=True,null=True)
	orderDimensionA1=models.CharField(max_length=100,blank=True,null=True)
	orderDimensionB1=models.CharField(max_length=100,blank=True,null=True)
	orderDimensionC1=models.CharField(max_length=100,blank=True,null=True)
	orderLength1=models.CharField(max_length=100,blank=True,null=True)
	orderNo2=models.CharField(max_length=100,blank=True,null=True)
	orderItem2=models.CharField(max_length=100,blank=True,null=True)
	shipedDate1=models.CharField(max_length=100,blank=True,null=True)
	custNo1=models.CharField(max_length=100,blank=True,null=True)
	orderTradeNo1=models.CharField(max_length=100,blank=True,null=True)
	adviceNo=models.CharField(max_length=100,blank=True,null=True)
	prodLineNo=models.CharField(max_length=100,blank=True,null=True)
	schdDate1=models.CharField(max_length=100,blank=True,null=True)
	schdSeq1=models.CharField(max_length=100,blank=True,null=True)
	prodClass=models.CharField(max_length=100,blank=True,null=True)
	stdClass=models.CharField(max_length=100,blank=True,null=True)
	MscNo=models.CharField(max_length=100,blank=True,null=True)
	orderSectionType=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SR_SAMPLINGID(models.Model):
	samplingId=models.CharField(max_length=30,primary_key=True)
	stdProdCode=models.CharField(max_length=100,blank=True,null=True)
	isTQPass=models.CharField(max_length=100,blank=True,null=True)
	errMsg=models.CharField(max_length=2000,blank=True,null=True)
	confirmEmpl=models.CharField(max_length=100,blank=True,null=True)
	confirmDate=models.CharField(max_length=100,blank=True,null=True)
	confirmTime=models.CharField(max_length=100,blank=True,null=True)
	sampSeqNo=models.CharField(max_length=100,blank=True,null=True)
	indexId=models.CharField(max_length=100,blank=True,null=True)
	reSamplingEmpl=models.CharField(max_length=100,blank=True,null=True)
	reSamplingDate=models.CharField(max_length=100,blank=True,null=True)
	reSamplingTime=models.CharField(max_length=100,blank=True,null=True)
	prodLineNo=models.CharField(max_length=100,blank=True,null=True)
	samplingShift=models.CharField(max_length=100,blank=True,null=True)
	entrustOrderNo=models.CharField(max_length=100,blank=True,null=True)
	sampleType=models.CharField(max_length=100,blank=True,null=True)
	samplingStatus=models.CharField(max_length=100,blank=True,null=True)
	isReSampling=models.CharField(max_length=100,blank=True,null=True)
	isCancel=models.CharField(max_length=100,blank=True,null=True)
	samplingIdMan=models.CharField(max_length=100,blank=True,null=True)
	entrustEmpl=models.CharField(max_length=100,blank=True,null=True)
	entrustDate=models.CharField(max_length=100,blank=True,null=True)
	entrustTime=models.CharField(max_length=100,blank=True,null=True)
	rollDate=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

#销售数据模型
class SALES_AREANO(models.Model):
	areaNo=models.CharField(max_length=30,primary_key=True)
	areaName=models.CharField(max_length=100,blank=True,null=True)
	status=models.CharField(max_length=100,blank=True,null=True)
	createEmpNo=models.CharField(max_length=100,blank=True,null=True)
	createDate=models.CharField(max_length=100,blank=True,null=True)
	createTime=models.CharField(max_length=100,blank=True,null=True)
	updateEmpNo=models.CharField(max_length=100,blank=True,null=True)
	updateDate=models.CharField(max_length=100,blank=True,null=True)
	updateTime=models.CharField(max_length=100,blank=True,null=True)
	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SALES_CUSTNO(models.Model):
	custNo=models.CharField(max_length=30,primary_key=True)
	recName=models.CharField(max_length=100,blank=True,null=True)
	province=models.CharField(max_length=100,blank=True,null=True)
	city=models.CharField(max_length=100,blank=True,null=True)
	country=models.CharField(max_length=100,blank=True,null=True)
	recShortName=models.CharField(max_length=100,blank=True,null=True)
	recOrderNo=models.CharField(max_length=100,blank=True,null=True)
	phone=models.CharField(max_length=100,blank=True,null=True)
	transWayNo=models.CharField(max_length=100,blank=True,null=True)
	recAddr=models.CharField(max_length=100,blank=True,null=True)
	memo=models.CharField(max_length=100,blank=True,null=True)
	status=models.CharField(max_length=100,blank=True,null=True)
	createEmpNo=models.CharField(max_length=100,blank=True,null=True)
	createDate=models.CharField(max_length=100,blank=True,null=True)
	createTime=models.CharField(max_length=100,blank=True,null=True)
	updateEmpNo=models.CharField(max_length=100,blank=True,null=True)
	updateDate=models.CharField(max_length=100,blank=True,null=True)
	updateTime=models.CharField(max_length=100,blank=True,null=True)
	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SALES_HARBORID(models.Model):
	harborId=models.CharField(max_length=30,primary_key=True)
	harborName=models.CharField(max_length=100,blank=True,null=True)
	status=models.CharField(max_length=100,blank=True,null=True)
	createEmpNo=models.CharField(max_length=100,blank=True,null=True)
	createDate=models.CharField(max_length=100,blank=True,null=True)
	createTime=models.CharField(max_length=100,blank=True,null=True)
	updateEmpNo=models.CharField(max_length=100,blank=True,null=True)
	updateDate=models.CharField(max_length=100,blank=True,null=True)
	updateTime=models.CharField(max_length=100,blank=True,null=True)
	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SALES_NOID(models.Model):
	noId=models.CharField(max_length=30,primary_key=True)
	compId=models.CharField(max_length=100,blank=True,null=True)
	noName=models.CharField(max_length=100,blank=True,null=True)
	createEmpNo=models.CharField(max_length=100,blank=True,null=True)
	createDate=models.CharField(max_length=100,blank=True,null=True)
	createTime=models.CharField(max_length=100,blank=True,null=True)
	updateEmpNo=models.CharField(max_length=100,blank=True,null=True)
	updateDate=models.CharField(max_length=100,blank=True,null=True)
	updateTime=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SALES_ORDERNO(models.Model):
	orderNo=models.CharField(max_length=30,primary_key=True)
	orderDate=models.CharField(max_length=100,blank=True,null=True)
	crcy=models.CharField(max_length=100,blank=True,null=True)
	taxType=models.CharField(max_length=100,blank=True,null=True)
	taxRate=models.CharField(max_length=100,blank=True,null=True)
	orderWeight=models.CharField(max_length=100,blank=True,null=True)
	orderAmount=models.CharField(max_length=100,blank=True,null=True)
	custNo=models.CharField(max_length=100,blank=True,null=True)
	compId=models.CharField(max_length=100,blank=True,null=True)
	compNo=models.CharField(max_length=100,blank=True,null=True)
	orderVer=models.CharField(max_length=100,blank=True,null=True)
	status=models.CharField(max_length=100,blank=True,null=True)
	contractTypeA=models.CharField(max_length=100,blank=True,null=True)
	shipReqDateB=models.CharField(max_length=100,blank=True,null=True)
	shipReqDateA=models.CharField(max_length=100,blank=True,null=True)
	transWayNo=models.CharField(max_length=100,blank=True,null=True)
	salesType=models.CharField(max_length=100,blank=True,null=True)
	salesMan=models.CharField(max_length=100,blank=True,null=True)
	salesDept=models.CharField(max_length=100,blank=True,null=True)
	salesGroup=models.CharField(max_length=100,blank=True,null=True)
	shipTolMax=models.CharField(max_length=100,blank=True,null=True)
	shipTolMin=models.CharField(max_length=100,blank=True,null=True)
	downPayment=models.CharField(max_length=100,blank=True,null=True)
	downPaymentRatio=models.CharField(max_length=100,blank=True,null=True)
	fwEdit=models.CharField(max_length=100,blank=True,null=True)
	isGathered=models.CharField(max_length=100,blank=True,null=True)
	updateEmpNo=models.CharField(max_length=100,blank=True,null=True)
	updateDate=models.CharField(max_length=100,blank=True,null=True)
	updateTime=models.CharField(max_length=100,blank=True,null=True)
	createEmpNo=models.CharField(max_length=100,blank=True,null=True)
	createDate=models.CharField(max_length=100,blank=True,null=True)
	createTime=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SALES_REFID(models.Model):
	refId=models.CharField(max_length=30,primary_key=True)
	compId=models.CharField(max_length=100,blank=True,null=True)
	refName=models.CharField(max_length=100,blank=True,null=True)
	fieldA=models.CharField(max_length=100,blank=True,null=True)
	fieldB=models.CharField(max_length=100,blank=True,null=True)
	fieldC=models.CharField(max_length=100,blank=True,null=True)
	fieldD=models.CharField(max_length=100,blank=True,null=True)
	createEmpNo=models.CharField(max_length=100,blank=True,null=True)
	createDate=models.CharField(max_length=100,blank=True,null=True)
	createTime=models.CharField(max_length=100,blank=True,null=True)
	updateEmpNo=models.CharField(max_length=100,blank=True,null=True)
	updateDate=models.CharField(max_length=100,blank=True,null=True)
	updateTime=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SALES_SITENO(models.Model):
	siteNo=models.CharField(max_length=30,primary_key=True)
	siteChnName=models.CharField(max_length=100,blank=True,null=True)
	transWayNo=models.CharField(max_length=100,blank=True,null=True)
	areaNo=models.CharField(max_length=100,blank=True,null=True)
	siteEngName=models.CharField(max_length=100,blank=True,null=True)
	status=models.CharField(max_length=100,blank=True,null=True)
	createEmpNo=models.CharField(max_length=100,blank=True,null=True)
	createDate=models.CharField(max_length=100,blank=True,null=True)
	createTime=models.CharField(max_length=100,blank=True,null=True)
	updateEmpNo=models.CharField(max_length=100,blank=True,null=True)
	updateDate=models.CharField(max_length=100,blank=True,null=True)
	updateTime=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SALES_LOADNO(models.Model):
	loadNo=models.CharField(max_length=30,primary_key=True)
	compId=models.CharField(max_length=100,blank=True,null=True)
	tranType=models.CharField(max_length=100,blank=True,null=True)
	collectNo=models.CharField(max_length=100,blank=True,null=True)
	collectType=models.CharField(max_length=100,blank=True,null=True)
	orderNo=models.CharField(max_length=100,blank=True,null=True)
	orderItem=models.CharField(max_length=100,blank=True,null=True)
	deliveryNo=models.CharField(max_length=100,blank=True,null=True)
	dispListNo=models.CharField(max_length=100,blank=True,null=True)
	dispSource=models.CharField(max_length=100,blank=True,null=True)
	transWayNo=models.CharField(max_length=100,blank=True,null=True)
	custNo=models.CharField(max_length=100,blank=True,null=True)
	recOrderNo=models.CharField(max_length=100,blank=True,null=True)
	prodClass=models.CharField(max_length=100,blank=True,null=True)
	prodType=models.CharField(max_length=100,blank=True,null=True)
	tradeNo=models.CharField(max_length=100,blank=True,null=True)
	prodLine=models.CharField(max_length=100,blank=True,null=True)
	plateNo=models.CharField(max_length=100,blank=True,null=True)
	carCompId=models.CharField(max_length=100,blank=True,null=True)
	unitPrice=models.CharField(max_length=100,blank=True,null=True)
	countWgtMode=models.CharField(max_length=100,blank=True,null=True)
	transWgt=models.CharField(max_length=100,blank=True,null=True)
	transAmt=models.CharField(max_length=100,blank=True,null=True)
	transAmtNoTax=models.CharField(max_length=100,blank=True,null=True)
	freightPrice=models.CharField(max_length=100,blank=True,null=True)
	transWay=models.CharField(max_length=100,blank=True,null=True)
	isSettled=models.CharField(max_length=100,blank=True,null=True)
	settleDate=models.CharField(max_length=100,blank=True,null=True)
	settleTime=models.CharField(max_length=100,blank=True,null=True)
	seqNo=models.CharField(max_length=100,blank=True,null=True)
	specMark=models.CharField(max_length=100,blank=True,null=True)
	planDeliQty=models.CharField(max_length=100,blank=True,null=True)
	planDeliWgt=models.CharField(max_length=100,blank=True,null=True)
	creditChkQty=models.CharField(max_length=100,blank=True,null=True)
	creditChkWgt=models.CharField(max_length=100,blank=True,null=True)
	transWayType=models.CharField(max_length=100,blank=True,null=True)
	assignQty=models.CharField(max_length=100,blank=True,null=True)
	assignWgt=models.CharField(max_length=100,blank=True,null=True)
	assignTWgt=models.CharField(max_length=100,blank=True,null=True)
	assignNWgt=models.CharField(max_length=100,blank=True,null=True)
	loadQty=models.CharField(max_length=100,blank=True,null=True)
	loadWgt=models.CharField(max_length=100,blank=True,null=True)
	loadTWgt=models.CharField(max_length=100,blank=True,null=True)
	loadNWgt=models.CharField(max_length=100,blank=True,null=True)
	realQty=models.CharField(max_length=100,blank=True,null=True)
	realWgt=models.CharField(max_length=100,blank=True,null=True)
	realTWgt=models.CharField(max_length=100,blank=True,null=True)
	realNWgt=models.CharField(max_length=100,blank=True,null=True)
	isGathered=models.CharField(max_length=100,blank=True,null=True)
	reWeigh=models.CharField(max_length=100,blank=True,null=True)
	scaleStatus=models.CharField(max_length=100,blank=True,null=True)
	isCarryByCust=models.CharField(max_length=100,blank=True,null=True)
	loadKind=models.CharField(max_length=100,blank=True,null=True)
	planDate=models.CharField(max_length=100,blank=True,null=True)
	shipDate=models.CharField(max_length=100,blank=True,null=True)
	autoGen=models.CharField(max_length=100,blank=True,null=True)
	assignEmpNo=models.CharField(max_length=100,blank=True,null=True)
	assignDate=models.CharField(max_length=100,blank=True,null=True)
	assignTime=models.CharField(max_length=100,blank=True,null=True)
	loadEmpNo=models.CharField(max_length=100,blank=True,null=True)
	loadDate=models.CharField(max_length=100,blank=True,null=True)
	loadTime=models.CharField(max_length=100,blank=True,null=True)
	outFactoryEmpNo=models.CharField(max_length=100,blank=True,null=True)
	outFactoryDate=models.CharField(max_length=100,blank=True,null=True)
	outFactoryTime=models.CharField(max_length=100,blank=True,null=True)
	closeEmpNo=models.CharField(max_length=100,blank=True,null=True)
	closeDate=models.CharField(max_length=100,blank=True,null=True)
	closeTime=models.CharField(max_length=100,blank=True,null=True)
	emptyCarWgt=models.CharField(max_length=100,blank=True,null=True)
	status=models.CharField(max_length=100,blank=True,null=True)
	isAssignFee=models.CharField(max_length=100,blank=True,null=True)
	isMakeCard=models.CharField(max_length=100,blank=True,null=True)
	isEnterFactory=models.CharField(max_length=100,blank=True,null=True)
	createEmpNo052=models.CharField(max_length=100,blank=True,null=True)
	createDate052=models.CharField(max_length=100,blank=True,null=True)
	createTime052=models.CharField(max_length=100,blank=True,null=True)
	updateEmpNo052=models.CharField(max_length=100,blank=True,null=True)
	updateDate052=models.CharField(max_length=100,blank=True,null=True)
	updateTime052=models.CharField(max_length=100,blank=True,null=True)
	createEmpNo121=models.CharField(max_length=100,blank=True,null=True)
	createDate121=models.CharField(max_length=100,blank=True,null=True)
	createTime121=models.CharField(max_length=100,blank=True,null=True)
	updateEmpNo121=models.CharField(max_length=100,blank=True,null=True)
	updateDate121=models.CharField(max_length=100,blank=True,null=True)
	updateTime121=models.CharField(max_length=100,blank=True,null=True)
	createEmpNo122=models.CharField(max_length=100,blank=True,null=True)
	createDate122=models.CharField(max_length=100,blank=True,null=True)
	createTime122=models.CharField(max_length=100,blank=True,null=True)
	updateEmpNo122=models.CharField(max_length=100,blank=True,null=True)
	updateDate122=models.CharField(max_length=100,blank=True,null=True)
	updateTime122=models.CharField(max_length=100,blank=True,null=True)
	createEmpNo131=models.CharField(max_length=100,blank=True,null=True)
	createDate131=models.CharField(max_length=100,blank=True,null=True)
	createTime131=models.CharField(max_length=100,blank=True,null=True)
	updateEmpNo131=models.CharField(max_length=100,blank=True,null=True)
	updateDate131=models.CharField(max_length=100,blank=True,null=True)
	updateTime131=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SALES_RECEIVENO(models.Model):
	receiveNo=models.CharField(max_length=30,primary_key=True)
	loadNo=models.CharField(max_length=100,blank=True,null=True)
	receiveQty=models.CharField(max_length=100,blank=True,null=True)
	receiveWgt=models.CharField(max_length=100,blank=True,null=True)
	receiveTWgt=models.CharField(max_length=100,blank=True,null=True)
	moveType=models.CharField(max_length=100,blank=True,null=True)
	warehouseNo=models.CharField(max_length=100,blank=True,null=True)
	status=models.CharField(max_length=100,blank=True,null=True)
	confirmEmpNo=models.CharField(max_length=100,blank=True,null=True)
	confirmDate=models.CharField(max_length=100,blank=True,null=True)
	confirmTime=models.CharField(max_length=100,blank=True,null=True)
	cancelEmpNo=models.CharField(max_length=100,blank=True,null=True)
	cancelDate=models.CharField(max_length=100,blank=True,null=True)
	cancelTime=models.CharField(max_length=100,blank=True,null=True)
	updateEmpNo=models.CharField(max_length=100,blank=True,null=True)
	updateDate=models.CharField(max_length=100,blank=True,null=True)
	updateTime=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SALES_RTNNO(models.Model):
	rtnNo=models.CharField(max_length=30,primary_key=True)
	compId=models.CharField(max_length=100,blank=True,null=True)
	custNo=models.CharField(max_length=100,blank=True,null=True)
	prodClass=models.CharField(max_length=100,blank=True,null=True)
	prodType=models.CharField(max_length=100,blank=True,null=True)
	orderNo=models.CharField(max_length=100,blank=True,null=True)
	orderItem=models.CharField(max_length=100,blank=True,null=True)
	plateNo=models.CharField(max_length=100,blank=True,null=True)
	prodLine=models.CharField(max_length=100,blank=True,null=True)
	tradeNo=models.CharField(max_length=100,blank=True,null=True)
	isChangeGood=models.CharField(max_length=100,blank=True,null=True)
	isDI=models.CharField(max_length=100,blank=True,null=True)
	planRtnQty=models.CharField(max_length=100,blank=True,null=True)
	planRtnWgt=models.CharField(max_length=100,blank=True,null=True)
	rtnQty=models.CharField(max_length=100,blank=True,null=True)
	rtnWgt=models.CharField(max_length=100,blank=True,null=True)
	unitPrice=models.CharField(max_length=100,blank=True,null=True)
	chgOrderNo=models.CharField(max_length=100,blank=True,null=True)
	chgOrderItem=models.CharField(max_length=100,blank=True,null=True)
	rtnReason=models.CharField(max_length=100,blank=True,null=True)
	rtnDesc=models.CharField(max_length=100,blank=True,null=True)
	status=models.CharField(max_length=100,blank=True,null=True)
	confirmEmpNo=models.CharField(max_length=100,blank=True,null=True)
	confirmDate=models.CharField(max_length=100,blank=True,null=True)
	confirmTime=models.CharField(max_length=100,blank=True,null=True)
	createEmpNo=models.CharField(max_length=100,blank=True,null=True)
	createDate=models.CharField(max_length=100,blank=True,null=True)
	createTime=models.CharField(max_length=100,blank=True,null=True)
	updateEmpNo=models.CharField(max_length=100,blank=True,null=True)
	updateDate=models.CharField(max_length=100,blank=True,null=True)
	updateTime=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SALES_LABELNO(models.Model):
	labelNo=models.CharField(max_length=30,primary_key=True)
	compId=models.CharField(max_length=100,blank=True,null=True)
	orderNo=models.CharField(max_length=100,blank=True,null=True)
	orderItem=models.CharField(max_length=100,blank=True,null=True)
	seqNo=models.CharField(max_length=100,blank=True,null=True)
	type1=models.CharField(max_length=100,blank=True,null=True)
	rtnNo=models.CharField(max_length=100,blank=True,null=True)
	rtntype=models.CharField(max_length=100,blank=True,null=True)
	deliveryNo=models.CharField(max_length=100,blank=True,null=True)
	dispListNo=models.CharField(max_length=100,blank=True,null=True)
	prodClass=models.CharField(max_length=100,blank=True,null=True)
	prodTypeNo=models.CharField(max_length=100,blank=True,null=True)
	prodType=models.CharField(max_length=100,blank=True,null=True)
	prodLine=models.CharField(max_length=100,blank=True,null=True)
	tradeNo=models.CharField(max_length=100,blank=True,null=True)
	heatNo=models.CharField(max_length=100,blank=True,null=True)
	rollNo=models.CharField(max_length=100,blank=True,null=True)
	rtnQty=models.CharField(max_length=100,blank=True,null=True)
	rtnWgt=models.CharField(max_length=100,blank=True,null=True)
	labelWgt=models.CharField(max_length=100,blank=True,null=True)
	labelThick=models.CharField(max_length=100,blank=True,null=True)
	labelWidth=models.CharField(max_length=100,blank=True,null=True)
	labelLength=models.CharField(max_length=100,blank=True,null=True)
	warehouseNo=models.CharField(max_length=100,blank=True,null=True)
	newLabelNo=models.CharField(max_length=100,blank=True,null=True)
	createBySys=models.CharField(max_length=100,blank=True,null=True)
	createEmpNo121=models.CharField(max_length=100,blank=True,null=True)
	createDate121=models.CharField(max_length=100,blank=True,null=True)
	createTime121=models.CharField(max_length=100,blank=True,null=True)
	createEmpNo032=models.CharField(max_length=100,blank=True,null=True)
	createDate032=models.CharField(max_length=100,blank=True,null=True)
	createTime032=models.CharField(max_length=100,blank=True,null=True)
	updateEmpNo032=models.CharField(max_length=100,blank=True,null=True)
	updateDate032=models.CharField(max_length=100,blank=True,null=True)
	updateTime032=models.CharField(max_length=100,blank=True,null=True)
	tallyNo=models.CharField(max_length=100,blank=True,null=True)
	customerNo=models.CharField(max_length=100,blank=True,null=True)
	datacreateDate=models.CharField(max_length=100,blank=True,null=True)
	datacreateTime=models.CharField(max_length=100,blank=True,null=True)
	psrNo=models.CharField(max_length=100,blank=True,null=True)
	thick=models.CharField(max_length=100,blank=True,null=True)
	width=models.CharField(max_length=100,blank=True,null=True)
	length=models.CharField(max_length=100,blank=True,null=True)
	thickUnit=models.CharField(max_length=100,blank=True,null=True)
	lengthUnit=models.CharField(max_length=100,blank=True,null=True)
	widthUnit=models.CharField(max_length=100,blank=True,null=True)
	shipWeight=models.CharField(max_length=100,blank=True,null=True)
	shipPcs=models.CharField(max_length=100,blank=True,null=True)
	qualityClass=models.CharField(max_length=100,blank=True,null=True)
	specMark=models.CharField(max_length=100,blank=True,null=True)
	coilNo=models.CharField(max_length=100,blank=True,null=True)
	salesType_1=models.CharField(max_length=100,blank=True,null=True)
	shipDate=models.CharField(max_length=100,blank=True,null=True)
	dataTypeNo=models.CharField(max_length=100,blank=True,null=True)
	tcLabel=models.CharField(max_length=100,blank=True,null=True)
	status=models.CharField(max_length=100,blank=True,null=True)
	createEmp=models.CharField(max_length=100,blank=True,null=True)
	cancelDate=models.CharField(max_length=100,blank=True,null=True)
	cancelTime=models.CharField(max_length=100,blank=True,null=True)
	cancelEmp=models.CharField(max_length=100,blank=True,null=True)
	prodDate=models.CharField(max_length=100,blank=True,null=True)
	createDate=models.CharField(max_length=100,blank=True,null=True)
	seq=models.CharField(max_length=100,blank=True,null=True)
	customerNameCh=models.CharField(max_length=100,blank=True,null=True)
	customerNameEn=models.CharField(max_length=100,blank=True,null=True)
	productNameCh=models.CharField(max_length=100,blank=True,null=True)
	productNameEn=models.CharField(max_length=100,blank=True,null=True)
	sendAddNo=models.CharField(max_length=100,blank=True,null=True)
	sendAddName=models.CharField(max_length=100,blank=True,null=True)
	custCopy=models.CharField(max_length=100,blank=True,null=True)
	exportCopy=models.CharField(max_length=100,blank=True,null=True)
	techTerms=models.CharField(max_length=100,blank=True,null=True)
	msc=models.CharField(max_length=100,blank=True,null=True)
	endDescCode=models.CharField(max_length=100,blank=True,null=True)
	lotNo=models.CharField(max_length=100,blank=True,null=True)
	shipWgt=models.CharField(max_length=100,blank=True,null=True)
	generateFrom=models.CharField(max_length=100,blank=True,null=True)
	dataFrom=models.CharField(max_length=100,blank=True,null=True)
	fromDate=models.CharField(max_length=100,blank=True,null=True)
	fromTime=models.CharField(max_length=100,blank=True,null=True)
	mscIndexNo=models.CharField(max_length=100,blank=True,null=True)
	LQIndexNo=models.CharField(max_length=100,blank=True,null=True)
	sizeMark=models.CharField(max_length=100,blank=True,null=True)
	salesType_2=models.CharField(max_length=100,blank=True,null=True)
	sampleIdNum=models.CharField(max_length=100,blank=True,null=True)
	carNo=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])


class SALES_DISPLISTNO(models.Model):
	dispListNo=models.CharField(max_length=30,primary_key=True)
	areaNo=models.CharField(max_length=100,blank=True,null=True)
	endLocNo=models.CharField(max_length=100,blank=True,null=True)
	orderNo=models.CharField(max_length=100,blank=True,null=True)
	orderItem=models.CharField(max_length=100,blank=True,null=True)
	planDeliQty=models.CharField(max_length=100,blank=True,null=True)
	planDeliWgt=models.CharField(max_length=100,blank=True,null=True)
	planDeliAmt=models.CharField(max_length=100,blank=True,null=True)
	realDeliQty=models.CharField(max_length=100,blank=True,null=True)
	realDeliWgt=models.CharField(max_length=100,blank=True,null=True)
	realDeliAmt=models.CharField(max_length=100,blank=True,null=True)
	assignQty=models.CharField(max_length=100,blank=True,null=True)
	assignWgt=models.CharField(max_length=100,blank=True,null=True)
	loadQty=models.CharField(max_length=100,blank=True,null=True)
	loadWgt=models.CharField(max_length=100,blank=True,null=True)
	unitPrice=models.CharField(max_length=100,blank=True,null=True)
	prodAmt=models.CharField(max_length=100,blank=True,null=True)
	transUnitPrice=models.CharField(max_length=100,blank=True,null=True)
	transAmt=models.CharField(max_length=100,blank=True,null=True)
	compNo=models.CharField(max_length=100,blank=True,null=True)
	dispSource=models.CharField(max_length=100,blank=True,null=True)
	autoGen=models.CharField(max_length=100,blank=True,null=True)
	salesType=models.CharField(max_length=100,blank=True,null=True)
	salesMan=models.CharField(max_length=100,blank=True,null=True)
	salesDept=models.CharField(max_length=100,blank=True,null=True)
	prodClass=models.CharField(max_length=100,blank=True,null=True)
	prodType=models.CharField(max_length=100,blank=True,null=True)
	recOrderNo=models.CharField(max_length=100,blank=True,null=True)
	certifyPostNo=models.CharField(max_length=100,blank=True,null=True)
	invPostNo=models.CharField(max_length=100,blank=True,null=True)
	countWgtMode=models.CharField(max_length=100,blank=True,null=True)
	dispValidDate=models.CharField(max_length=100,blank=True,null=True)
	transWayNo=models.CharField(max_length=100,blank=True,null=True)
	beginLocNo=models.CharField(max_length=100,blank=True,null=True)
	beginHarborId=models.CharField(max_length=100,blank=True,null=True)
	endHarborId=models.CharField(max_length=100,blank=True,null=True)
	beginStockId=models.CharField(max_length=100,blank=True,null=True)
	endStockId=models.CharField(max_length=100,blank=True,null=True)
	transWay=models.CharField(max_length=100,blank=True,null=True)
	crcy=models.CharField(max_length=100,blank=True,null=True)
	prodLine=models.CharField(max_length=100,blank=True,null=True)
	leaveFactory=models.CharField(max_length=100,blank=True,null=True)
	isGathered=models.CharField(max_length=100,blank=True,null=True)
	reWeigh=models.CharField(max_length=100,blank=True,null=True)
	millCopy=models.CharField(max_length=100,blank=True,null=True)
	carCompId=models.CharField(max_length=100,blank=True,null=True)
	dispItemStatus=models.CharField(max_length=100,blank=True,null=True)
	status=models.CharField(max_length=100,blank=True,null=True)
	effectEmpNo=models.CharField(max_length=100,blank=True,null=True)
	effectDate=models.CharField(max_length=100,blank=True,null=True)
	effectTime=models.CharField(max_length=100,blank=True,null=True)
	unEffectEmpNo=models.CharField(max_length=100,blank=True,null=True)
	unEffectDate=models.CharField(max_length=100,blank=True,null=True)
	unEffectTime=models.CharField(max_length=100,blank=True,null=True)
	closeEmpNo=models.CharField(max_length=100,blank=True,null=True)
	closeDate=models.CharField(max_length=100,blank=True,null=True)
	closeTime=models.CharField(max_length=100,blank=True,null=True)
	unCloseEmpNo=models.CharField(max_length=100,blank=True,null=True)
	unCloseDate=models.CharField(max_length=100,blank=True,null=True)
	unCloseTime=models.CharField(max_length=100,blank=True,null=True)
	createEmpNo=models.CharField(max_length=100,blank=True,null=True)
	createDate1=models.CharField(max_length=100,blank=True,null=True)
	createTime=models.CharField(max_length=100,blank=True,null=True)
	updateEmpNo=models.CharField(max_length=100,blank=True,null=True)
	updateDate=models.CharField(max_length=100,blank=True,null=True)
	updateTime=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SALES_MILLSHEETNO(models.Model):
	millSheetNo=models.CharField(max_length=30,primary_key=True)
	compId=models.CharField(max_length=100,blank=True,null=True)
	prodClass=models.CharField(max_length=100,blank=True,null=True)
	prodType=models.CharField(max_length=100,blank=True,null=True)
	inOutSale=models.CharField(max_length=100,blank=True,null=True)
	salesType=models.CharField(max_length=100,blank=True,null=True)
	customerNo=models.CharField(max_length=100,blank=True,null=True)
	customerNameCh=models.CharField(max_length=100,blank=True,null=True)
	customerNameEn=models.CharField(max_length=150,blank=True,null=True)
	psrNo=models.CharField(max_length=100,blank=True,null=True)
	productNameCh=models.CharField(max_length=100,blank=True,null=True)
	productNameEn=models.CharField(max_length=150,blank=True,null=True)
	orderNo=models.CharField(max_length=100,blank=True,null=True)
	item=models.CharField(max_length=100,blank=True,null=True)
	tallyNo=models.CharField(max_length=100,blank=True,null=True)
	deliveryNo=models.CharField(max_length=100,blank=True,null=True)
	blNo=models.CharField(max_length=100,blank=True,null=True)
	shipDate=models.CharField(max_length=100,blank=True,null=True)
	techTerms=models.CharField(max_length=200,blank=True,null=True)
	sendAddNo=models.CharField(max_length=100,blank=True,null=True)
	sendAddName=models.CharField(max_length=100,blank=True,null=True)
	custCopy=models.CharField(max_length=100,blank=True,null=True)
	exportCopy=models.CharField(max_length=100,blank=True,null=True)
	statusCode=models.CharField(max_length=100,blank=True,null=True)
	thickUnit=models.CharField(max_length=100,blank=True,null=True)
	widthUnit=models.CharField(max_length=100,blank=True,null=True)
	lengthUnit=models.CharField(max_length=100,blank=True,null=True)
	msc=models.CharField(max_length=100,blank=True,null=True)
	mscIndexNo=models.CharField(max_length=400,blank=True,null=True)
	tradeNo=models.CharField(max_length=100,blank=True,null=True)
	qualityClass=models.CharField(max_length=100,blank=True,null=True)
	carNo=models.CharField(max_length=100,blank=True,null=True)
	memoA=models.CharField(max_length=500,blank=True,null=True)
	memoB=models.CharField(max_length=500,blank=True,null=True)
	memoC=models.CharField(max_length=1500,blank=True,null=True)
	memoD=models.CharField(max_length=500,blank=True,null=True)
	memoE=models.CharField(max_length=100,blank=True,null=True)
	memoF=models.CharField(max_length=100,blank=True,null=True)
	LQIndexNo=models.CharField(max_length=100,blank=True,null=True)
	endDescCode=models.CharField(max_length=100,blank=True,null=True)
	title=models.CharField(max_length=150,blank=True,null=True)
	seq=models.CharField(max_length=100,blank=True,null=True)
	letterSeq=models.CharField(max_length=100,blank=True,null=True)
	createDate=models.CharField(max_length=100,blank=True,null=True)
	createEmp=models.CharField(max_length=100,blank=True,null=True)
	reviseDate=models.CharField(max_length=100,blank=True,null=True)
	reviseEmp=models.CharField(max_length=100,blank=True,null=True)
	reviseNo=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SALES_COLLECTNO(models.Model):
	collectNo=models.CharField(max_length=30,primary_key=True)
	collectType=models.CharField(max_length=100,blank=True,null=True)
	recOrderNo=models.CharField(max_length=100,blank=True,null=True)
	warehouseNo=models.CharField(max_length=100,blank=True,null=True)
	beginHarborId=models.CharField(max_length=100,blank=True,null=True)
	endHarborId=models.CharField(max_length=100,blank=True,null=True)
	shipName=models.CharField(max_length=100,blank=True,null=True)
	ser=models.CharField(max_length=100,blank=True,null=True)
	informDate=models.CharField(max_length=100,blank=True,null=True)
	leaveHarborDate=models.CharField(max_length=100,blank=True,null=True)
	remark=models.CharField(max_length=100,blank=True,null=True)
	status=models.CharField(max_length=100,blank=True,null=True)
	loadShip=models.CharField(max_length=100,blank=True,null=True)
	effectEmpNo=models.CharField(max_length=100,blank=True,null=True)
	effectDate=models.CharField(max_length=100,blank=True,null=True)
	effectTime=models.CharField(max_length=100,blank=True,null=True)
	unEffectEmpNo=models.CharField(max_length=100,blank=True,null=True)
	unEffectDate=models.CharField(max_length=100,blank=True,null=True)
	unEffectTime=models.CharField(max_length=100,blank=True,null=True)
	createEmpNo=models.CharField(max_length=100,blank=True,null=True)
	createDate=models.CharField(max_length=100,blank=True,null=True)
	createTime=models.CharField(max_length=100,blank=True,null=True)
	updateEmpNo=models.CharField(max_length=100,blank=True,null=True)
	updateDate=models.CharField(max_length=100,blank=True,null=True)
	updateTime=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

# #复合主键
class SALES2_NOID_NOSTYLE(models.Model):
	noId=models.CharField(max_length=30,blank=True)
	noStyle=models.CharField(max_length=30,blank=True)
	compId=models.CharField(max_length=100,blank=True,null=True)
	noCount=models.CharField(max_length=100,blank=True,null=True)
	createEmpNo=models.CharField(max_length=100,blank=True,null=True)
	createDate=models.CharField(max_length=100,blank=True,null=True)
	createTime=models.CharField(max_length=100,blank=True,null=True)
	updateEmpNo=models.CharField(max_length=100,blank=True,null=True)
	updateDate=models.CharField(max_length=100,blank=True,null=True)
	updateTime=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SALES2_NOID_RULEID(models.Model):
	noId=models.CharField(max_length=30,blank=True)
	ruleId=models.CharField(max_length=30,blank=True)
	compId=models.CharField(max_length=100,blank=True,null=True)
	ruleName=models.CharField(max_length=100,blank=True,null=True)
	ruleType=models.CharField(max_length=100,blank=True,null=True)
	ruleLength=models.CharField(max_length=100,blank=True,null=True)
	ruleConstant=models.CharField(max_length=100,blank=True,null=True)
	ruleRenew=models.CharField(max_length=100,blank=True,null=True)
	createEmpNo=models.CharField(max_length=100,blank=True,null=True)
	createDate=models.CharField(max_length=100,blank=True,null=True)
	createTime=models.CharField(max_length=100,blank=True,null=True)
	updateEmpNo=models.CharField(max_length=100,blank=True,null=True)
	updateDate=models.CharField(max_length=100,blank=True,null=True)
	updateTime=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SALES2_LINEUPLOGNO_SPECKIND(models.Model):
	lineUpLogNo=models.CharField(max_length=30,blank=True)
	specKind=models.CharField(max_length=30,blank=True)
	compId=models.CharField(max_length=100,blank=True,null=True)
	orderItemNo=models.CharField(max_length=100,blank=True,null=True)
	lineUpDate=models.CharField(max_length=100,blank=True,null=True)
	lineUpEmpL=models.CharField(max_length=100,blank=True,null=True)
	lineUpTime=models.CharField(max_length=100,blank=True,null=True)
	orderNo=models.CharField(max_length=100,blank=True,null=True)
	orderItem=models.CharField(max_length=100,blank=True,null=True)
	psrNo=models.CharField(max_length=100,blank=True,null=True)
	apnNo=models.CharField(max_length=100,blank=True,null=True)
	mscNo=models.CharField(max_length=100,blank=True,null=True)
	sizeA=models.CharField(max_length=100,blank=True,null=True)
	sizeB=models.CharField(max_length=100,blank=True,null=True)
	sizeC=models.CharField(max_length=100,blank=True,null=True)
	tradeNo=models.CharField(max_length=100,blank=True,null=True)
	lineUpStatus=models.CharField(max_length=100,blank=True,null=True)
	sizeDesc=models.CharField(max_length=100,blank=True,null=True)
	matNo=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SALES2_MILLSHEETNO_SAMPLEID(models.Model):
	millSheetNo=models.CharField(max_length=30,blank=True)
	sampleId=models.CharField(max_length=30,blank=True)
	compId=models.CharField(max_length=100,blank=True,null=True)
	item_1=models.CharField(max_length=100,blank=True,null=True)
	labelNo=models.CharField(max_length=100,blank=True,null=True)
	sampleSeqNo=models.CharField(max_length=100,blank=True,null=True)
	heatNo=models.CharField(max_length=100,blank=True,null=True)
	lotNo=models.CharField(max_length=100,blank=True,null=True)
	coilNo=models.CharField(max_length=100,blank=True,null=True)
	lengthUnit=models.CharField(max_length=100,blank=True,null=True)
	shipPcs=models.CharField(max_length=100,blank=True,null=True)
	shipWeight=models.CharField(max_length=100,blank=True,null=True)
	errorCheck=models.CharField(max_length=100,blank=True,null=True)
	createDate=models.CharField(max_length=100,blank=True,null=True)
	createEmp=models.CharField(max_length=100,blank=True,null=True)
	reviseDate=models.CharField(max_length=100,blank=True,null=True)
	reviseEmp=models.CharField(max_length=100,blank=True,null=True)
	reviseNo=models.CharField(max_length=100,blank=True,null=True)
	prodDate=models.CharField(max_length=100,blank=True,null=True)
	prodClass=models.CharField(max_length=100,blank=True,null=True)
	prodTypeNo=models.CharField(max_length=100,blank=True,null=True)
	seq=models.CharField(max_length=100,blank=True,null=True)
	orderNo=models.CharField(max_length=100,blank=True,null=True)
	item_2=models.CharField(max_length=100,blank=True,null=True)
	tallyNo=models.CharField(max_length=100,blank=True,null=True)
	deliveryNo=models.CharField(max_length=100,blank=True,null=True)
	shipDate=models.CharField(max_length=100,blank=True,null=True)
	psrNo=models.CharField(max_length=100,blank=True,null=True)
	customerNo=models.CharField(max_length=100,blank=True,null=True)
	customerNameCh=models.CharField(max_length=100,blank=True,null=True)
	customerNameEn=models.CharField(max_length=100,blank=True,null=True)
	productNameCh=models.CharField(max_length=100,blank=True,null=True)
	productNameEn=models.CharField(max_length=100,blank=True,null=True)
	sendAddNo=models.CharField(max_length=100,blank=True,null=True)
	sendAddName=models.CharField(max_length=100,blank=True,null=True)
	blNo=models.CharField(max_length=100,blank=True,null=True)
	custCopy=models.CharField(max_length=100,blank=True,null=True)
	exportCopy=models.CharField(max_length=100,blank=True,null=True)
	techTerms=models.CharField(max_length=100,blank=True,null=True)
	msc=models.CharField(max_length=100,blank=True,null=True)
	endDescCode=models.CharField(max_length=100,blank=True,null=True)
	length=models.CharField(max_length=100,blank=True,null=True)
	shipWgt=models.CharField(max_length=100,blank=True,null=True)
	generateFrom=models.CharField(max_length=100,blank=True,null=True)
	dataFrom=models.CharField(max_length=100,blank=True,null=True)
	fromDate=models.CharField(max_length=100,blank=True,null=True)
	fromTime=models.CharField(max_length=100,blank=True,null=True)
	mscIndexNo=models.CharField(max_length=100,blank=True,null=True)
	LQIndexNo=models.CharField(max_length=100,blank=True,null=True)
	sizeMark=models.CharField(max_length=100,blank=True,null=True)
	salesType=models.CharField(max_length=100,blank=True,null=True)
	sampleIdNum=models.CharField(max_length=100,blank=True,null=True)
	tradeNo=models.CharField(max_length=100,blank=True,null=True)
	carNo=models.CharField(max_length=100,blank=True,null=True)
	tclabel=models.CharField(max_length=100,blank=True,null=True)
	thick=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SALES2_MILLSHEETNO_SPECCODE(models.Model):
	millSheetNo=models.CharField(max_length=30,blank=True)
	specCode=models.CharField(max_length=30,blank=True)
	compId=models.CharField(max_length=100,blank=True,null=True)
	specType=models.CharField(max_length=100,blank=True,null=True)
	testType=models.CharField(max_length=100,blank=True,null=True)
	sampStatus=models.CharField(max_length=100,blank=True,null=True)
	direct=models.CharField(max_length=100,blank=True,null=True)
	posA=models.CharField(max_length=100,blank=True,null=True)
	posB=models.CharField(max_length=100,blank=True,null=True)
	chemDj=models.CharField(max_length=100,blank=True,null=True)
	unit=models.CharField(max_length=100,blank=True,null=True)
	specMin=models.CharField(max_length=100,blank=True,null=True)
	specMax=models.CharField(max_length=100,blank=True,null=True)
	createDate=models.CharField(max_length=100,blank=True,null=True)
	createEmp=models.CharField(max_length=100,blank=True,null=True)
	reviseDate=models.CharField(max_length=100,blank=True,null=True)
	reviseEmp=models.CharField(max_length=100,blank=True,null=True)
	reviseNo=models.CharField(max_length=100,blank=True,null=True)
	seqNo=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SALES2_ORDERNO_ORDERITEM(models.Model):
	orderNo=models.CharField(max_length=30,blank=True)
	orderItem=models.CharField(max_length=30,blank=True)
	compId=models.CharField(max_length=100,blank=True,null=True)
	orderVer=models.CharField(max_length=100,blank=True,null=True)
	status=models.CharField(max_length=100,blank=True,null=True)
	lineupStatus=models.CharField(max_length=100,blank=True,null=True)
	contractTypeA=models.CharField(max_length=100,blank=True,null=True)
	contractTypeB=models.CharField(max_length=100,blank=True,null=True)
	contractTypeC=models.CharField(max_length=100,blank=True,null=True)
	prodClass=models.CharField(max_length=100,blank=True,null=True)
	prodDetailClass=models.CharField(max_length=100,blank=True,null=True)
	prodType=models.CharField(max_length=100,blank=True,null=True)
	prodKind=models.CharField(max_length=100,blank=True,null=True)
	psrNo=models.CharField(max_length=100,blank=True,null=True)
	apnNo=models.CharField(max_length=100,blank=True,null=True)
	standName=models.CharField(max_length=100,blank=True,null=True)
	tradeNo=models.CharField(max_length=100,blank=True,null=True)
	mscNo=models.CharField(max_length=100,blank=True,null=True)
	quality=models.CharField(max_length=100,blank=True,null=True)
	priority=models.CharField(max_length=100,blank=True,null=True)
	netWeightShipYN=models.CharField(max_length=100,blank=True,null=True)
	countWgtMode=models.CharField(max_length=100,blank=True,null=True)
	downPaymentYN=models.CharField(max_length=100,blank=True,null=True)
	orderWeight=models.CharField(max_length=100,blank=True,null=True)
	orderQty=models.CharField(max_length=100,blank=True,null=True)
	specialPriceFlag=models.CharField(max_length=100,blank=True,null=True)
	basePrice=models.CharField(max_length=100,blank=True,null=True)
	orderPrice=models.CharField(max_length=100,blank=True,null=True)
	freightPrice=models.CharField(max_length=100,blank=True,null=True)
	downPaymentRatio=models.CharField(max_length=100,blank=True,null=True)
	downPayment=models.CharField(max_length=100,blank=True,null=True)
	shipReqDateA=models.CharField(max_length=100,blank=True,null=True)
	shipReqDateB=models.CharField(max_length=100,blank=True,null=True)
	slabType=models.CharField(max_length=100,blank=True,null=True)
	cutType=models.CharField(max_length=100,blank=True,null=True)
	orderDiameter=models.CharField(max_length=100,blank=True,null=True)
	orderDiameterUnit=models.CharField(max_length=100,blank=True,null=True)
	orderThick=models.CharField(max_length=100,blank=True,null=True)
	orderThickUnit=models.CharField(max_length=100,blank=True,null=True)
	orderWidth=models.CharField(max_length=100,blank=True,null=True)
	orderWidthUnit=models.CharField(max_length=100,blank=True,null=True)
	orderLength=models.CharField(max_length=100,blank=True,null=True)
	orderLengthUnit=models.CharField(max_length=100,blank=True,null=True)
	orderDiameterMin=models.CharField(max_length=100,blank=True,null=True)
	orderDiameterMax=models.CharField(max_length=100,blank=True,null=True)
	orderThickMin=models.CharField(max_length=100,blank=True,null=True)
	orderThickMax=models.CharField(max_length=100,blank=True,null=True)
	orderWidthMax=models.CharField(max_length=100,blank=True,null=True)
	orderWidthMin=models.CharField(max_length=100,blank=True,null=True)
	orderLengthMax=models.CharField(max_length=100,blank=True,null=True)
	orderLengthMin=models.CharField(max_length=100,blank=True,null=True)
	shipTolMax=models.CharField(max_length=100,blank=True,null=True)
	shipTolMin=models.CharField(max_length=100,blank=True,null=True)
	minCoilWeight=models.CharField(max_length=100,blank=True,null=True)
	maxCoilWeight=models.CharField(max_length=100,blank=True,null=True)
	packCode=models.CharField(max_length=100,blank=True,null=True)
	minShortLength=models.CharField(max_length=100,blank=True,null=True)
	maxShortLength=models.CharField(max_length=100,blank=True,null=True)
	bundleType=models.CharField(max_length=100,blank=True,null=True)
	specialReqCodeL=models.CharField(max_length=100,blank=True,null=True)
	ultrasonicYN=models.CharField(max_length=100,blank=True,null=True)
	eddyCurrentYN=models.CharField(max_length=100,blank=True,null=True)
	specMark=models.CharField(max_length=100,blank=True,null=True)
	closeReason=models.CharField(max_length=100,blank=True,null=True)
	closeEmpNo=models.CharField(max_length=100,blank=True,null=True)
	closeDate=models.CharField(max_length=100,blank=True,null=True)
	closeTime=models.CharField(max_length=100,blank=True,null=True)
	unCloseEmpNo=models.CharField(max_length=100,blank=True,null=True)
	unCloseDate=models.CharField(max_length=100,blank=True,null=True)
	unCloseTime=models.CharField(max_length=100,blank=True,null=True)
	smEdit=models.CharField(max_length=100,blank=True,null=True)
	enlace=models.CharField(max_length=100,blank=True,null=True)
	deleteReason=models.CharField(max_length=100,blank=True,null=True)
	deleteEmpNo=models.CharField(max_length=100,blank=True,null=True)
	deleteDate=models.CharField(max_length=100,blank=True,null=True)
	deleteTime=models.CharField(max_length=100,blank=True,null=True)
	dispWeight=models.CharField(max_length=100,blank=True,null=True)
	dispQty=models.CharField(max_length=100,blank=True,null=True)
	deliWeight=models.CharField(max_length=100,blank=True,null=True)
	deliQty=models.CharField(max_length=100,blank=True,null=True)
	chgWeight=models.CharField(max_length=100,blank=True,null=True)
	chgQty=models.CharField(max_length=100,blank=True,null=True)
	chgDeliWeight=models.CharField(max_length=100,blank=True,null=True)
	chgDeliQty=models.CharField(max_length=100,blank=True,null=True)
	packWire=models.CharField(max_length=100,blank=True,null=True)
	ironWire=models.CharField(max_length=100,blank=True,null=True)
	pcsOfBdl=models.CharField(max_length=100,blank=True,null=True)
	multipleLength=models.CharField(max_length=100,blank=True,null=True)
	packMaterialWeight=models.CharField(max_length=100,blank=True,null=True)
	reWeigh=models.CharField(max_length=100,blank=True,null=True)
	memo=models.CharField(max_length=100,blank=True,null=True)
	confirmEmpNo=models.CharField(max_length=100,blank=True,null=True)
	confirmDate=models.CharField(max_length=100,blank=True,null=True)
	confirmTime=models.CharField(max_length=100,blank=True,null=True)
	cancelEmpNo=models.CharField(max_length=100,blank=True,null=True)
	cancelDate=models.CharField(max_length=100,blank=True,null=True)
	cancelTime=models.CharField(max_length=100,blank=True,null=True)
	createEmpNo=models.CharField(max_length=100,blank=True,null=True)
	createDate=models.CharField(max_length=100,blank=True,null=True)
	createTime=models.CharField(max_length=100,blank=True,null=True)
	updateEmpNo=models.CharField(max_length=100,blank=True,null=True)
	updateDate=models.CharField(max_length=100,blank=True,null=True)
	updateTime=models.CharField(max_length=100,blank=True,null=True)
	orderItemNo=models.CharField(max_length=100,blank=True,null=True)
	updateDate101=models.CharField(max_length=100,blank=True,null=True)
	updateTime101=models.CharField(max_length=100,blank=True,null=True)
	updateEmpL101=models.CharField(max_length=100,blank=True,null=True)
	updateDept101=models.CharField(max_length=100,blank=True,null=True)
	lineUpCause=models.CharField(max_length=100,blank=True,null=True)
	procRange=models.CharField(max_length=100,blank=True,null=True)
	failureDate=models.CharField(max_length=100,blank=True,null=True)
	failureTime=models.CharField(max_length=100,blank=True,null=True)
	sizeDesc=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class SALES2_REFID_SUBID(models.Model):
	refId=models.CharField(max_length=30,blank=True)
	subId=models.CharField(max_length=30,blank=True)
	compId=models.CharField(max_length=100,blank=True,null=True)
	valueA=models.CharField(max_length=100,blank=True,null=True)
	valueB=models.CharField(max_length=100,blank=True,null=True)
	valueC=models.CharField(max_length=100,blank=True,null=True)
	valueD=models.CharField(max_length=100,blank=True,null=True)
	valueE=models.CharField(max_length=100,blank=True,null=True)
	valueF=models.CharField(max_length=100,blank=True,null=True)
	valueG=models.CharField(max_length=100,blank=True,null=True)
	valueH=models.CharField(max_length=100,blank=True,null=True)
	createEmpNo=models.CharField(max_length=100,blank=True,null=True)
	createDate=models.CharField(max_length=100,blank=True,null=True)
	createTime=models.CharField(max_length=100,blank=True,null=True)
	updateEmpNo=models.CharField(max_length=100,blank=True,null=True)
	updateDate=models.CharField(max_length=100,blank=True,null=True)
	updateTime=models.CharField(max_length=100,blank=True,null=True)

	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

class Information(models.Model):
	title = models.CharField(max_length=150)
	subtitle = models.CharField(max_length=150,null=True,blank=True)
	link = models.CharField(max_length=150,null=True,blank=True)
	content = models.TextField(blank=True)
	pub_date = models.DateTimeField('date published', auto_now_add=True)
	last_edit_date = models.DateTimeField('last edited', auto_now=True)
	publisher = models.CharField(max_length=30)
	infotype = models.IntegerField()
	#type={1:"页面底部导航栏"，2:“核心模块入口”}
	def set_attr(self,**kwargs):
		#print(kwargs.items())
		for item in kwargs.items():
			for each in item[1].items():
				#print('{0}:{1}'.format(each[0],each[1]))
				setattr(self,each[0],each[1])

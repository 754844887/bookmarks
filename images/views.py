from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import ImageCreateForm
from django.contrib import messages
from django.shortcuts import get_object_or_404
from .models import Image
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from common.decorators import ajax_required
from actions.utils import create_action
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

import redis
from django.conf import settings


r = redis.StrictRedis(host=settings.REDIS_HOST,
					port=settings.REDIS_PORT,
					db=settings.REDIS_DB)


@login_required
def image_create(request):
	if request.method == 'POST':
		form = ImageCreateForm(request.POST)
		if form.is_valid():
			cd = form.cleaned_data
			new_item = form.save(commit=False)
			new_item.user = request.user
			new_item.save()
			create_action(request.user, 'bookmarked image', new_item)
			messages.success(request, 'Image added successfully')
			return redirect(new_item.get_absolute_url())
	else:
		form = ImageCreateForm(data=request.GET)
	return render(request, 'images/image/create.html', {'section': 'images','form': form})


@login_required
def image_detail(request, id, slug):
	image = get_object_or_404(Image, id=id, slug=slug)
	total_views = r.incr('image:{}:views'.format(image.id))
	r.zincrby('image_ranking', 1, image.id)
	return render(request, 'images/image/detail.html', {'section':'images', 'image':image, 'total_views': total_views})



@ajax_required
@login_required
@require_POST
def image_like(request):
    image_id = request.POST.get('id')
    action = request.POST.get('action')
    if image_id and action:
        try:
            image = Image.objects.get(id=image_id)
            if action == 'like':
                image.user_like.add(request.user)
                create_action(request.user, 'likes', image)
            else:
                image.user_like.remove(request.user)
            return JsonResponse({'status':'ok'})
        except:
            pass
    return JsonResponse({'status':'ko'})


@login_required
def image_list(request):
    images = Image.objects.all()
    paginator = Paginator(images, 16)
    page = request.GET.get('page') # 获取前端请求的页码
    try:
        """
         注意不能使用get_page方法，get_page方法
         会自动判断EmptyPage，返回最后一页       
        """
        images = paginator.page(page) # 获取对应页码的内容
    except PageNotAnInteger:
        # If page is not an integer deliver the first page
        images = paginator.page(1) # 如果页码为非整数，返回第一页
    except EmptyPage:
        if request.is_ajax():
            # If the request is AJAX and the page is out of range
            # return an empty page
            return HttpResponse('')
        # If page is out of range deliver last page of results
        images = paginator.page(paginator.num_pages) # 如果页码为空则返回最后一页
    if request.is_ajax():
	    # "$('#image-list').append(data)",ajax 函数中的data部分来自list_ajax.html
        return render(request,
                      'images/image/list_ajax.html',
                      {'section': 'images', 'images': images})
    return render(request,
                  'images/image/list.html',
                   {'section': 'images', 'images': images})


@login_required
def image_ranking(request):
	image_ranking = r.zrevrange('image_ranking', 0, 9) # 返回有序集中指定区间内的成员，通过索引，分数从高到底
	image_ranking_ids = [int(id) for id in image_ranking] # 返回image对象的id列表
	# get most viewed images
	most_viewed = list(Image.objects.filter(
		id__in=image_ranking_ids))            # 返回image对象的列表
	most_viewed.sort(key=lambda x: image_ranking_ids.index(x.id)) # 取出image对象的id 值并根据该值在image_ranking_ids 列表中的索引顺序进行排序
	return render(request,
	              'images/image/ranking.html',
	              {'section': 'images',
	               'most_viewed': most_viewed})

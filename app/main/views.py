# -*- coding: utf-8 -*-
from datetime import datetime
from flask import render_template,session,redirect,url_for,request,abort,flash,g,jsonify
from flask.ext.login import login_required,current_user
from flask.ext.paginate import Pagination
from MU_utils import GetNamespace
from .. model import User,Page
from datetime import datetime
import pdb
from collections import OrderedDict
from .form import PushForm,EditProfileForm,AddUserForm,AdminEditProfileForm,BanKeywordForm,LimitKeywordForm
from . import main
from MU_update import ForbiddenItemsFilter,ForbiddenItemPushed,ForbiddenItemGet
from MU_utils import GetNamespace
from MU_weibo import RefreshCode
import sys
reload(sys)
sys.setdefaultencoding('utf8')
@main.before_request
@login_required
def before_request():
    g.user = current_user.id
    if current_user.is_blocked(g.user):
        return render_template('block.html')
@main.route('/')
def index():
    return render_template('index.html')
@main.route('/update',methods=['GET','POST'])
@login_required
def update():
    p=Page()
    title=[]
    u=User()
    title=p.GetTitles()
    titles=[]
    pushtime = u.GetPushtime(g.user)
    deltime = u.GetDeltime(g.user)
    jsondata=request.get_json()
    total=len(title)
    page = request.args.get('page',1,type=int)
    per_page=10
    offset=(page - 1) * per_page
    for i in range(len(title)):
        if i < per_page and (offset+i) < len(title):
            titles.append(title[offset+i])
        else:
            break
    pagination=Pagination(css_framework='bootstrap3',link_size='sm',show_single_page=False,page=page,per_page=per_page,total=total,format_total=True,format_number=True)
    if request.method == 'POST' and jsondata['action'] == 'post':
        if pushtime is not '0':
            title=jsondata['title']
            flag=p.Break(title)
            if flag==True:
                p.RecordUpdate(title,current_user.id,'推送')
                pass
            else: 
                abort(403)
        else:
            abort(403)
    if request.method == 'POST' and jsondata['action'] == 'del':
        if deltime is not '0':
            title=jsondata['title']
            flag=p.Delete(title)
            if flag==True:
                p.RecordUpdate(title,current_user.id,'删除')
                pass
            else:
                abort(403)
    return render_template('update.html',titles=titles,current_time=datetime.utcnow(),pushtime=pushtime,deltime=deltime,page=page,per_page=per_page,pagination=pagination)
@main.route('/mupdate',methods=['GET','POST'])
@login_required
def mupdate():
    p=Page()
    u=User()
    pushtime = u.GetPushtime(g.user)
    deltime = u.GetDeltime(g.user)
    form=PushForm(request.form)
    if request.method == 'POST' and form.validate():
        if pushtime is not '0':
            title=form.pushtitle.data
            ns=GetNamespace(title)
            if ns is 0:
                forbiddenflag=ForbiddenItemsFilter(title)
                pushedflag=ForbiddenItemPushed(title)
                getflag=ForbiddenItemGet(title)
                if forbiddenflag is True and pushedflag is True and getflag is True:
                    flag=p.Add(title)
                    if flag is True:
                        p.RecordUpdate(title,current_user.id,'手动推送')
                        flash('推送成功，本条目将在下一次推送时被推送')
                        return redirect('/mupdate')
                    else:
                        flash('错误-条目图片不符合要求')
                else:
                    flash('错误-条目被屏蔽推送或已被更新姬自动获取')
            else:
                flash('错误-条目不在主名字空间')
        else:
            flash('错误-请检查本日推送次数')
    return render_template('mupdate.html',form=form,pushtime=pushtime)
@main.route('/user/<username>')
@login_required
def user(username):
    u=User()
    adminflag=current_user.is_administrator(g.user)
    if g.user == username or adminflag is True:
        flag=u.CheckUser(username)
        if flag is False:
            abort(404)
        u.GetUserInfo(username)
        return render_template('user.html',u=u,username=username)
    else:
        abort(403)
@main.route('/userlist',methods=['GET','POST'])
@login_required
def userlist():
    u=User()
    form=AddUserForm()
    flag=current_user.is_administrator(g.user)
    if flag is True:
        userlist=u.GetUserList()
        jsondata=request.get_json()
        if request.method == 'POST' and jsondata:
            if jsondata['action'] == u'edit':
                username=jsondata['username']
                location=url_for('.admin_edit_profile',username=username)
                return jsonify({"status":302,"location":location})
            else:
                username=jsondata['username']
                u.RemUser(username)
                return redirect('userlist')
        elif request.method == 'POST' and form.validate():
            pwd=u.GetPassword(g.user)
            if u.verify_password(form.oripassword.data):
                u.AddUser(form.username.data,form.password.data,form.role.data,form.email.data)
                return redirect('userlist')
        else:
            return render_template('userlist.html',userlist=userlist,form=form)
    else:
        abort(403)
@main.route('/edit_profile',methods=['GET','POST'])
@login_required
def edit_profile():
    form=EditProfileForm()
    u=User()
    if request.method == 'POST' and form.validate():
        pwd=u.GetPassword(g.user)
        if u.verify_password(form.oripassword.data):
            email=form.email.data
            aboutme=form.about_me.data
            if form.password.data is not u'':
                u.ChangePassword(g.user,form.password.data)
            u.ChangeProfile(g.user,email,aboutme)
            flash('成功更新资料')
            return redirect(url_for('.user',username=g.user))
        else:
            flash('原密码输入错误！')
    u.GetUserInfo(g.user)
    form.email.data=u.email
    form.about_me.data=u.aboutme
    return render_template('edit_profile.html',form=form,u=u)
@main.route('/edit_profile/<username>',methods=['GET','POST'])
@login_required
def admin_edit_profile(username):
    u=User()
    form=AdminEditProfileForm()
    flag=current_user.is_administrator(g.user)
    if request.method == 'POST' and form.validate():
        if flag is True:
            pwd=u.GetPassword(g.user)
            if u.verify_password(form.oripassword.data):
                email=form.email.data
                aboutme=form.about_me.data
                role=form.role.data
                if form.password.data is not u'':
                    u.ChangePassword(username,form.password.data)
                u.AdminChangeProfile(username,email,role,aboutme)
                flash('成功更新资料')
                return redirect(url_for('.user',username=username))
            else:
                flash('管理员密码输入错误！')
        else:
            abort(403)
    u.GetUserInfo(username)
    form.email.data=u.email
    form.about_me.data=u.aboutme
    form.role.data=u.role
    return render_template('admin_edit_profile.html',form=form,u=u)
@main.route('/log')
@login_required
def log():
    flag=current_user.is_administrator(g.user)
    if flag is True:
        p=Page()
        record=p.GetRecord()
        records={}
        records=OrderedDict()
        total=len(record)
        page = request.args.get('page',1,type=int)
        per_page=10
        keys=record.keys()
        offset=(page - 1) * per_page
        for i in range(len(keys)):
            if i < per_page and (offset+i) < len(keys):
                records[keys[offset+i]]=record[keys[offset+i]]
            else:
                break
        pagination=Pagination(css_framework='bootstrap3',link_size='sm',show_single_page=False,page=page,per_page=per_page,total=total,format_total=True,format_number=True)
        return render_template('log.html',records=records,page=page,per_page=per_page,pagination=pagination)  
    else:
        abort(403)


@main.route('/ban',methods=['GET','POST'])
@login_required
def ban():
    flag=current_user.is_administrator(g.user)
    if flag is True:
        form=BanKeywordForm()
        p = Page()
        jsondata=request.get_json()
        if request.method == 'POST':
            if jsondata:
                keyword = jsondata['keyword']
                p.DelBan(keyword)
                flash('成功删除关键词')
                location=url_for('.ban')
                return jsonify({"status":302,"location":location})
            if form.validate():
                keyword = form.keyword.data
                p.AddBan(keyword)
                flash('成功添加关键词')
                return redirect('ban')
        banlist = p.GetBan()
        keywords = []
        total = len(banlist)
        page = request.args.get('page', 1, type=int)
        per_page = 10
        offset = (page - 1) * per_page
        for i in range(len(banlist)):
            if i < per_page and (offset+i) < len(banlist):
                keywords.append(banlist[offset+i])
            else:
                break
        pagination=Pagination(css_framework='bootstrap3',link_size='sm',show_single_page=False,page=page,per_page=per_page,total=total,format_total=True,format_number=True)
        return render_template('ban.html',keywords=keywords,page=page,per_page=per_page,pagination=pagination,form=form)
    else:
        abort(403)
@main.route('/code')
@login_required
def code():
    code=request.args.get('code')
    flag=RefreshCode(code)
    if flag is True:
        return render_template('success.html')
    else:
        return render_template('failed.html',e=flag)

@main.route('/limit')
@login_required
def limit():
    flag=current_user.is_administrator(g.user)
    if flag is True:
        form = LimitKeywordForm()
        




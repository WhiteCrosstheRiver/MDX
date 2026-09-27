#!/usr/bin/env python
# coding: utf-8
import matplotlib
matplotlib.use('Agg')  # 必须在导入 pyplot 之前设置

from pylab import *
loss = loadtxt('loss.out')
plt.rcParams["font.weight"] = "bold"
plt.rcParams["axes.labelweight"] = "bold"
plt.rc('font',family='Times New Roman',size = 12) 
# font = {'family': 'serif', 'serif': 'Times New Roman', 'weight': 'normal', 'size': 10}
# plt.rc('font', **font)
figure(figsize=(10, 8))
subplot(2,2,1)
ax1 = plt.gca()
loglog(loss[:, 1:4])
loglog(loss[:, 7:10])
xlabel('Generation/100')
ylabel('Loss')
legend(['Total', 'L1-regularization', 'L2-regularization', 'Energy-test', 'Force-test','Virial-test'] )
subplot(2,2,2)
ax2 = plt.gca()
energy_test = loadtxt('energy_test.out')
import matplotlib.pyplot as plt
plt.scatter(energy_test[:, 1], energy_test[:, 0],s=12., c='k')
energy_max=np.max(energy_test[:, 0:2])
energy_min=np.min(energy_test[:, 0:2])

delta = energy_max - energy_min
plot(linspace(energy_min-0.02*delta,energy_max+0.02*delta), linspace(energy_min-0.02*delta,energy_max+0.02*delta), '-',color = 'red')
plt.xlim(energy_min-0.02*delta,energy_max+0.02*delta)
plt.ylim(energy_min-0.02*delta,energy_max+0.02*delta)

b0 = delta/4
step0 = float('%.2f' % b0)
x_major_locator0=MultipleLocator(step0)
y_major_locator0=MultipleLocator(step0)
ax2.xaxis.set_major_locator(x_major_locator0)
ax2.yaxis.set_major_locator(y_major_locator0)

rmse = np.sqrt(np.mean((energy_test[:, 1]-energy_test[:, 0])**2))*1000


plt.text(0.95,0.1,"RMSE: {:.3f} meV/atom".format(rmse), 
         horizontalalignment='right',verticalalignment='center',fontsize=12,transform = ax2.transAxes)
             

xlabel('DFT energy (eV/atom)')
ylabel('NEP energy (eV/atom)')

subplot(2,2,3)
ax3 = plt.gca()
force_test = loadtxt('force_test.out')

plot(force_test[:, 3:6], force_test[:, 0:3], '.')
rmse = np.sqrt(np.mean((force_test[:, 3:6]-force_test[:, 0:3])**2))
             
force_max=np.max(force_test[:, 0:6])
force_min=np.min(force_test[:, 0:6])


delta = force_max - force_min
b = delta/4
step = float('%.2f' % b)
x_major_locator=MultipleLocator(step)
y_major_locator=MultipleLocator(step)
ax3.xaxis.set_major_locator(x_major_locator)
ax3.yaxis.set_major_locator(y_major_locator)

plot(linspace(force_min-0.02*delta,force_max+0.02*delta), linspace(force_min-0.02*delta,force_max+0.02*delta), '-',color = 'red')
plt.xlim(force_min-0.02*delta,force_max+0.02*delta)
plt.ylim(force_min-0.02*delta,force_max+0.02*delta)

xlabel('DFT force (eV/Å)')
ylabel('NEP force (eV/Å)')

plt.text(0.95,0.1,"RMSE: {:.3f} eV/Å".format(rmse), 
         horizontalalignment='right',verticalalignment='center',fontsize=12,transform = ax3.transAxes)
legend(['x direction', 'y direction', 'z direction'])
subplot(2,2,4)

ax4 = plt.gca()
virial_test = loadtxt('virial_test.out')
column_num = virial_test.shape[1]
if column_num == 2:
    virial_max=np.max(virial_test[:, 0:2])
    virial_min=np.min(virial_test[:, 0:2])
    plot(virial_test[:, 1], virial_test[:, 0], '.')
    rmse = np.sqrt(np.mean((virial_test[:, 1]-virial_test[:, 0])**2))*1000
elif column_num == 12:
    virial_max=np.max(virial_test[:, 0:12])
    virial_min=np.min(virial_test[:, 0:12])
    plot(virial_test[:, 6:].reshape(-1), virial_test[:, :6].reshape(-1), '.')
    rmse = np.sqrt(np.mean((virial_test[:, :6].reshape(-1)-virial_test[:, 6:].reshape(-1))**2))*1000


delta = virial_max - virial_min    
plot(linspace(virial_min-0.02*delta,virial_max+0.02*delta), linspace(virial_min-0.02*delta,virial_max+0.02*delta), '-',color = 'red')    
plt.xlim(virial_min-0.02*delta,virial_max+0.02*delta)
plt.ylim(virial_min-0.02*delta,virial_max+0.02*delta)    
b1 = delta/4
step1 = float('%.2f' % b1)
x_major_locator1=MultipleLocator(step1)
y_major_locator1=MultipleLocator(step1)
ax4.xaxis.set_major_locator(x_major_locator1)
ax4.yaxis.set_major_locator(y_major_locator1)
xlabel('DFT virial (eV/atom)')
ylabel('NEP virial (eV/atom)')

ax = plt.gca()
plt.text(0.95,0.1,"RMSE: {:.3f} meV/atom".format(rmse), 
          horizontalalignment='right',verticalalignment='center',fontsize=12,transform = ax.transAxes)

subplots_adjust(hspace = 0.25, wspace = 0.3)
plt.savefig('test_result.jpg',dpi = 300)

###########################画训练集#############################
plt.cla()
loss = loadtxt('loss.out')
plt.rcParams["font.weight"] = "bold"
plt.rcParams["axes.labelweight"] = "bold"
plt.rc('font',family='Times New Roman',size = 12) 
# font = {'family': 'serif', 'serif': 'Times New Roman', 'weight': 'normal', 'size': 10}
# plt.rc('font', **font)
figure(figsize=(10, 8))
subplot(2,2,1)
ax1 = plt.gca()
loglog(loss[:, 1:7])
# loglog(loss[:, 7:10])
xlabel('Generation/100')
ylabel('Loss')
legend(['Total', 'L1-regularization', 'L2-regularization', 'Energy-train', 'Force-train','Virial-train'] )
subplot(2,2,2)
ax2 = plt.gca()
energy_train = loadtxt('energy_train.out')
import matplotlib.pyplot as plt
plt.scatter(energy_train[:, 1], energy_train[:, 0],s=12., c='k')
energy_max=np.max(energy_train[:, 0:2])
energy_min=np.min(energy_train[:, 0:2])

delta = energy_max - energy_min

plot(linspace(energy_min-0.02*delta,energy_max+0.02*delta), linspace(energy_min-0.02*delta,energy_max+0.02*delta), '-',color = 'red')
plt.xlim(energy_min-0.02*delta,energy_max+0.02*delta)
plt.ylim(energy_min-0.02*delta,energy_max+0.02*delta)

b0 = delta/4
step0 = float('%.2f' % b0)
x_major_locator0=MultipleLocator(step0)
y_major_locator0=MultipleLocator(step0)
ax2.xaxis.set_major_locator(x_major_locator0)
ax2.yaxis.set_major_locator(y_major_locator0)

rmse = np.sqrt(np.mean((energy_train[:, 1]-energy_train[:, 0])**2))*1000


plt.text(0.95,0.1,"RMSE: {:.3f} meV/atom".format(rmse), 
         horizontalalignment='right',verticalalignment='center',fontsize=12,transform = ax2.transAxes)
             

xlabel('DFT energy (eV/atom)')
ylabel('NEP energy (eV/atom)')

subplot(2,2,3)
ax3 = plt.gca()
force_train = loadtxt('force_train.out')

plot(force_train[:, 3:6], force_train[:, 0:3], '.')
rmse = np.sqrt(np.mean((force_train[:, 3:6]-force_train[:, 0:3])**2))
             
force_max=np.max(force_train[:, 0:6])
force_min=np.min(force_train[:, 0:6])

delta = force_max - force_min
b = delta/4
step = float('%.2f' % b)
x_major_locator=MultipleLocator(step)
y_major_locator=MultipleLocator(step)
ax3.xaxis.set_major_locator(x_major_locator)
ax3.yaxis.set_major_locator(y_major_locator)

plot(linspace(force_min-0.02*delta,force_max+0.02*delta), linspace(force_min-0.02*delta,force_max+0.02*delta), '-',color = 'red')
plt.xlim(force_min-0.02*delta,force_max+0.02*delta)
plt.ylim(force_min-0.02*delta,force_max+0.02*delta)

xlabel('DFT force (eV/Å)')
ylabel('NEP force (eV/Å)')

plt.text(0.95,0.1,"RMSE: {:.3f} eV/Å".format(rmse), 
         horizontalalignment='right',verticalalignment='center',fontsize=12,transform = ax3.transAxes)
legend(['x direction', 'y direction', 'z direction'])
subplot(2,2,4)

ax4 = plt.gca()

virial_train = loadtxt('virial_train.out')
column_num = virial_train.shape[1]
if column_num == 2:
    virial_max=np.max(virial_train[:, 0:2])
    virial_min=np.min(virial_train[:, 0:2])
    plot(virial_train[:, 1], virial_train[:, 0], '.')
    rmse = np.sqrt(np.mean((virial_train[:, 1]-virial_train[:, 0])**2))*1000
elif column_num == 12:
    virial_max=np.max(virial_train[:, 0:12])
    virial_min=np.min(virial_train[:, 0:12])
    plot(virial_train[:, 6:].reshape(-1), virial_train[:, :6].reshape(-1), '.')
    rmse = np.sqrt(np.mean((virial_train[:, :6].reshape(-1)-virial_train[:, 6:].reshape(-1))**2))*1000


delta = virial_max - virial_min    
plot(linspace(virial_min-0.02*delta,virial_max+0.02*delta), linspace(virial_min-0.02*delta,virial_max+0.02*delta), '-',color = 'red')    
plt.xlim(virial_min-0.02*delta,virial_max+0.02*delta)
plt.ylim(virial_min-0.02*delta,virial_max+0.02*delta)    
b1 = delta/4
step1 = float('%.2f' % b1)
x_major_locator1=MultipleLocator(step1)
y_major_locator1=MultipleLocator(step1)
ax4.xaxis.set_major_locator(x_major_locator1)
ax4.yaxis.set_major_locator(y_major_locator1)
xlabel('DFT virial (eV/atom)')
ylabel('NEP virial (eV/atom)')

ax = plt.gca()
plt.text(0.95,0.1,"RMSE: {:.3f} meV/atom".format(rmse), 
          horizontalalignment='right',verticalalignment='center',fontsize=12,transform = ax.transAxes)

subplots_adjust(hspace = 0.25, wspace = 0.3)
plt.savefig('train_result.jpg',dpi = 300)

plt.cla()
plt.close()
plt.figure()
figure(figsize=(10, 4))
subplot(1,2,1)
restart = loadtxt('nep.restart')
restart[:,0] = np.log10(abs(restart[:,0]))
plt.hist(restart[:,0], bins=120, density=False , alpha=0.6,edgecolor='black')  # bins参数指定直方图的柱子数量，alpha参数设置透明度
plt.xlabel('log10(abs(para))')
plt.ylabel('counts')

subplot(1,2,2)

plt.hist(restart[:,1], bins=120, density=False , alpha=0.6,edgecolor='black',color='yellow')  # bins参数指定直方图的柱子数量，alpha参数设置透明度
plt.xlabel('para')
plt.ylabel('counts')
plt.tight_layout()
plt.savefig('Histogram.jpg',dpi = 300)

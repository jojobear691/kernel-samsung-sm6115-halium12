#!/usr/bin/env python3
"""Exercise the real DRM notifier with an asynchronous workqueue adapter.

The hardware worker is held at a condition variable until the test permits its
completion. Consumer-visible ordering, rather than the presence of a flush call,
is the assertion. This does not emulate the physical panel or prove bootability.
"""
import argparse
import pathlib
import re
import shlex
import subprocess
import tempfile

HARNESS = r'''
#define _GNU_SOURCE
#include <errno.h>
#include <pthread.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
#define HX_CONTAINER_SPEED_UP 1
#define msecs_to_jiffies(ms) (ms)
#define DRM_PANEL_EARLY_EVENT_BLANK 2
#define DRM_PANEL_EVENT_BLANK 1
#define DRM_PANEL_BLANK_UNBLANK 0
#define DRM_PANEL_BLANK_POWERDOWN 1
#define container_of(ptr,type,member) ((type *)((char *)(ptr)-offsetof(type,member)))
#define I(...) ((void)0)
struct notifier_block { int unused; };
struct workqueue_struct { int unused; };
struct delayed_work { pthread_t thread; int queued; int joined; };
struct himax_ts_data {
    struct notifier_block fb_notif;
    void *dev;
    int initialized;
    struct workqueue_struct *ts_int_workqueue;
    struct delayed_work ts_int_work;
};
struct drm_panel_notifier { void *data; unsigned id; unsigned refresh_rate; };
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t changed=PTHREAD_COND_INITIALIZER;
static int permit, ready, returning, joining, observed_ready, suspended;
static unsigned long event;
static struct himax_ts_data ts;
static struct workqueue_struct queue;
static struct drm_panel_notifier note;
static int blank;
static void *worker(void *unused) {
    (void)unused;
    pthread_mutex_lock(&lock);
    while (!permit) pthread_cond_wait(&changed,&lock);
    ready=1;
    pthread_cond_broadcast(&changed);
    pthread_mutex_unlock(&lock);
    return NULL;
}
static int queue_delayed_work(struct workqueue_struct *q,struct delayed_work *w,unsigned delay) {
    (void)q;(void)delay;
    if (w!=&ts.ts_int_work) abort();
    if (w->queued) return 0;
    w->queued=1;
    if (pthread_create(&w->thread,NULL,worker,NULL)) abort();
    return 1;
}
static int flush_delayed_work(struct delayed_work *w) {
    if (w!=&ts.ts_int_work) abort();
    pthread_mutex_lock(&lock);
    joining=1;
    pthread_cond_broadcast(&changed);
    pthread_mutex_unlock(&lock);
    if (w->queued&&!w->joined) { pthread_join(w->thread,NULL);w->joined=1; }
    return 1;
}
static int himax_common_suspend(void *dev) { (void)dev;suspended++;return 0; }
/* The real public-source callback is inserted here without rewriting it. */
__CALLBACK__
static void *invoke(void *unused) {
    (void)unused;
    int rc=drm_notifier_callback(&ts.fb_notif,event,&note);
    pthread_mutex_lock(&lock);
    observed_ready=ready;
    returning=1;
    if (rc) abort();
    pthread_cond_broadcast(&changed);
    pthread_mutex_unlock(&lock);
    return NULL;
}
static int run_case(const char *name,int prequeued,int ignored,int sleep_event) {
    memset(&ts,0,sizeof(ts));
    permit=ready=returning=joining=observed_ready=suspended=0;
    ts.dev=&ts;ts.initialized=1;ts.ts_int_workqueue=&queue;
    blank=sleep_event?DRM_PANEL_BLANK_POWERDOWN:DRM_PANEL_BLANK_UNBLANK;
    event=sleep_event?DRM_PANEL_EARLY_EVENT_BLANK:DRM_PANEL_EVENT_BLANK;
    note=(struct drm_panel_notifier){.id=ignored?0:29,.data=&blank,.refresh_rate=60};
    if (prequeued) queue_delayed_work(NULL,&ts.ts_int_work,0);
    pthread_t caller;
    pthread_create(&caller,NULL,invoke,NULL);
    pthread_mutex_lock(&lock);
    struct timespec deadline;clock_gettime(CLOCK_REALTIME,&deadline);deadline.tv_sec+=3;
    while (!returning&&!joining) {
        if (pthread_cond_timedwait(&changed,&lock,&deadline)==ETIMEDOUT) {
            fputs("callback did not progress\n",stderr);exit(3);
        }
    }
    permit=1;
    pthread_cond_broadcast(&changed);
    pthread_mutex_unlock(&lock);
    pthread_join(caller,NULL);
    if (ts.ts_int_work.queued&&!ts.ts_int_work.joined) pthread_join(ts.ts_int_work.thread,NULL);
    int pass=ignored?(!ts.ts_int_work.queued&&!suspended):
        sleep_event?(suspended==1&&!ts.ts_int_work.queued):observed_ready;
    printf("%s %s\n",pass?"PASS":"FAIL",name);
    return !pass;
}
int main(void) {
    alarm(15);
    int failures=0;
    failures+=run_case("unblank completes touch reset before panel consumer",0,0,0);
    failures+=run_case("already queued resume completes before panel consumer",1,0,0);
    failures+=run_case("unrelated panel notification schedules no resume",0,1,0);
    failures+=run_case("early powerdown retains suspend behavior",0,0,1);
    return failures?1:0;
}
'''

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('source',type=pathlib.Path)
    parser.add_argument('--cc',default='cc')
    parser.add_argument('--cflags',default='')
    args=parser.parse_args()
    source=args.source.read_text()
    match=re.search(r'^int drm_notifier_callback\(.*?^\}',source,re.M|re.S)
    if not match:
        raise SystemExit('DRM notifier callback missing from source')
    with tempfile.TemporaryDirectory(prefix='himax-resume-test-') as tmp:
        tmp=pathlib.Path(tmp)
        code=tmp/'test.c';exe=tmp/'test'
        code.write_text(HARNESS.replace('__CALLBACK__',match.group()))
        subprocess.run([args.cc,*shlex.split(args.cflags),'-std=gnu11','-O2','-Wall','-Wextra','-pthread',str(code),'-o',str(exe)],check=True)
        return subprocess.run([str(exe)],timeout=20).returncode

if __name__=='__main__':
    raise SystemExit(main())

from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from shared import ASYNC_ORDER_PROCESSING_TASK_QUEUE_NAME
from temporalio.workflow import ParentClosePolicy
import asyncio

## read more about what imports_passed_through are; most probably looks related to the pyenv libs
with workflow.unsafe.imports_passed_through():
    from activities import TxnProcessingActivities
    from shared import CartInfo
    import uuid

@workflow.defn
class PostProcessCartWorkflow:
    @workflow.run
    async def run_wf(self, cart: CartInfo) -> str:
        default_retry_policy = RetryPolicy(
            maximum_attempts=3,
            maximum_interval=timedelta(seconds=2),
            non_retryable_error_types=["NotEnoughBalance","InvalidCardError","Exception"],
        )

        indefinite_retry_policy = RetryPolicy(
            maximum_attempts=0,
            maximum_interval=timedelta(seconds=5),
            non_retryable_error_types=["Exception"],
        )
        #check customer_service
        customer_service_output = await workflow.execute_activity_method(
            TxnProcessingActivities.customer_service_activity,
            cart,
            start_to_close_timeout=timedelta(seconds=5),
            retry_policy=default_retry_policy,
        )
        #send_email_receipt
        send_email_receipt_output = await workflow.execute_activity_method(
            TxnProcessingActivities.send_email_receipt_activity,
            customer_service_output,
            start_to_close_timeout=timedelta(seconds=5),
            retry_policy=default_retry_policy,
        )
        #check customer_service
        await asyncio.sleep(30)
        send_email_offer_output = await workflow.execute_activity_method(
            TxnProcessingActivities.send_email_offer_activity,
            customer_service_output,
            start_to_close_timeout=timedelta(seconds=5),
            retry_policy=default_retry_policy,
        )

        return send_email_receipt_output + "|" + send_email_offer_output


@workflow.defn
class ProcessCartWorkflow:
    @workflow.run
    async def run_wf(self, cart: CartInfo) -> str:
        default_retry_policy = RetryPolicy(
            maximum_attempts=3,
            maximum_interval=timedelta(seconds=2),
            non_retryable_error_types=["NotEnoughBalance","InvalidCardError","Exception"],
        )

        indefinite_retry_policy = RetryPolicy(
            maximum_attempts=0,
            maximum_interval=timedelta(seconds=5),
            non_retryable_error_types=["Exception"],
        )

        #check balance
        check_balance_output = await workflow.execute_activity_method(
            TxnProcessingActivities.check_balance_activity,
            cart,
            start_to_close_timeout=timedelta(seconds=5),
            retry_policy=default_retry_policy,
        )
        #process payment
        process_payment_output = await workflow.execute_activity_method(
                TxnProcessingActivities.process_payment_activity,
                cart,
                start_to_close_timeout=timedelta(seconds=5),
                retry_policy=default_retry_policy,
        )

        try:
            submit_order_output = await workflow.execute_activity_method(
                TxnProcessingActivities.submit_order_activity,
                cart,
                start_to_close_timeout=timedelta(seconds=5),
                retry_policy=indefinite_retry_policy,
            )
        except Exception:
            refund_payment_output = await workflow.execute_activity_method(
                TxnProcessingActivities.refund_payment_activity,
                process_payment_output,
                start_to_close_timeout=timedelta(seconds=5),
                retry_policy=default_retry_policy,
            )
            return refund_payment_output

        #post processing
        submit_post_processing = await workflow.start_child_workflow(
            PostProcessCartWorkflow.run_wf,
            cart,
            task_queue=ASYNC_ORDER_PROCESSING_TASK_QUEUE_NAME,
            parent_close_policy=ParentClosePolicy.ABANDON
        )
        return check_balance_output + " | " + process_payment_output + " | " + submit_order_output + " | " + str(submit_post_processing)

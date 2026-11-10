<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && backlogItem" class="modal-overlay" @click="close">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">
              {{ mode === 'create' ? t('purchaseOrder.createTitle') : t('purchaseOrder.viewTitle') }}
            </h3>
            <button class="close-button" :aria-label="t('purchaseOrder.close')" @click="close">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <div class="item-header">
              <div>
                <h4 class="item-name">{{ translateProductName(backlogItem.item_name) }}</h4>
                <div class="item-sku">SKU: {{ backlogItem.item_sku }} · {{ backlogItem.order_id }}</div>
              </div>
              <div class="shortage">
                <div class="shortage-label">{{ t('purchaseOrder.shortage') }}</div>
                <div class="shortage-value">{{ shortage }}</div>
              </div>
            </div>

            <!-- Create mode -->
            <form v-if="mode === 'create'" class="po-form" @submit.prevent="submit">
              <label class="field">
                <span class="field-label">{{ t('purchaseOrder.supplier') }}</span>
                <input
                  v-model="form.supplier_name"
                  type="text"
                  :placeholder="t('purchaseOrder.supplierPlaceholder')"
                  required
                />
              </label>

              <div class="field-row">
                <label class="field">
                  <span class="field-label">{{ t('purchaseOrder.quantity') }}</span>
                  <input v-model.number="form.quantity" type="number" min="1" step="1" required />
                </label>
                <label class="field">
                  <span class="field-label">{{ t('purchaseOrder.unitCost') }}</span>
                  <input v-model.number="form.unit_cost" type="number" min="0" step="0.01" required />
                </label>
              </div>

              <label class="field">
                <span class="field-label">{{ t('purchaseOrder.expectedDelivery') }}</span>
                <input v-model="form.expected_delivery_date" type="date" :min="today" required />
              </label>

              <label class="field">
                <span class="field-label">{{ t('purchaseOrder.notes') }}</span>
                <textarea v-model="form.notes" rows="2"></textarea>
              </label>

              <div class="total-row">
                <span>{{ t('purchaseOrder.total') }}</span>
                <strong>{{ formatCurrencyWithDecimals(formTotal, currentCurrency, 2) }}</strong>
              </div>

              <p v-if="error" class="error-message" role="alert">{{ error }}</p>
            </form>

            <!-- View mode -->
            <div v-else>
              <div v-if="loading" class="state-message">{{ t('purchaseOrder.loading') }}</div>
              <p v-else-if="error" class="error-message" role="alert">{{ error }}</p>
              <div v-else-if="purchaseOrder" class="info-grid">
                <div class="info-item">
                  <div class="field-label">{{ t('purchaseOrder.poNumber') }}</div>
                  <div class="info-value mono">{{ purchaseOrder.id }}</div>
                </div>
                <div class="info-item">
                  <div class="field-label">{{ t('purchaseOrder.status') }}</div>
                  <div class="info-value"><span class="badge">{{ purchaseOrder.status }}</span></div>
                </div>
                <div class="info-item">
                  <div class="field-label">{{ t('purchaseOrder.supplier') }}</div>
                  <div class="info-value">{{ purchaseOrder.supplier_name }}</div>
                </div>
                <div class="info-item">
                  <div class="field-label">{{ t('purchaseOrder.quantity') }}</div>
                  <div class="info-value">{{ purchaseOrder.quantity.toLocaleString() }}</div>
                </div>
                <div class="info-item">
                  <div class="field-label">{{ t('purchaseOrder.total') }}</div>
                  <div class="info-value">
                    {{ formatCurrencyWithDecimals(purchaseOrder.quantity * purchaseOrder.unit_cost, currentCurrency, 2) }}
                  </div>
                </div>
                <div class="info-item">
                  <div class="field-label">{{ t('purchaseOrder.expectedDelivery') }}</div>
                  <div class="info-value">{{ purchaseOrder.expected_delivery_date }}</div>
                </div>
                <div class="info-item">
                  <div class="field-label">{{ t('purchaseOrder.createdDate') }}</div>
                  <div class="info-value">{{ formatDateTime(purchaseOrder.created_date) }}</div>
                </div>
                <div v-if="purchaseOrder.notes" class="info-item full">
                  <div class="field-label">{{ t('purchaseOrder.notes') }}</div>
                  <div class="info-value">{{ purchaseOrder.notes }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <template v-if="mode === 'create'">
              <button class="btn-secondary" type="button" @click="close">{{ t('purchaseOrder.cancel') }}</button>
              <button class="btn-primary" type="button" :disabled="submitting" @click="submit">
                {{ submitting ? t('purchaseOrder.submitting') : t('purchaseOrder.submit') }}
              </button>
            </template>
            <button v-else class="btn-secondary" type="button" @click="close">{{ t('purchaseOrder.close') }}</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script>
import { ref, computed, watch } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

const todayIso = () => {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export default {
  name: 'PurchaseOrderModal',
  props: {
    isOpen: {
      type: Boolean,
      default: false
    },
    backlogItem: {
      type: Object,
      default: null
    },
    mode: {
      type: String,
      default: 'create',
      validator: (value) => ['create', 'view'].includes(value)
    }
  },
  emits: ['close', 'po-created'],
  setup(props, { emit }) {
    const { t, currentCurrency, translateProductName } = useI18n()

    const form = ref({})
    const submitting = ref(false)
    const loading = ref(false)
    const error = ref(null)
    const purchaseOrder = ref(null)
    const today = todayIso()

    const shortage = computed(() => {
      if (!props.backlogItem) return 0
      return Math.max(props.backlogItem.quantity_needed - props.backlogItem.quantity_available, 0)
    })

    const formTotal = computed(() => {
      const qty = Number(form.value.quantity) || 0
      const cost = Number(form.value.unit_cost) || 0
      return qty * cost
    })

    const resetForm = () => {
      form.value = {
        supplier_name: '',
        quantity: shortage.value || 1,
        unit_cost: 0,
        expected_delivery_date: '',
        notes: ''
      }
    }

    const loadPurchaseOrder = async () => {
      try {
        loading.value = true
        error.value = null
        purchaseOrder.value = await api.getPurchaseOrderByBacklogItem(props.backlogItem.id)
      } catch (err) {
        purchaseOrder.value = null
        error.value = t('purchaseOrder.loadError')
        console.error('Failed to load purchase order:', err)
      } finally {
        loading.value = false
      }
    }

    const isValid = () => {
      const f = form.value
      return (
        f.supplier_name && f.supplier_name.trim() &&
        Number.isInteger(f.quantity) && f.quantity > 0 &&
        typeof f.unit_cost === 'number' && f.unit_cost >= 0 &&
        /^\d{4}-\d{2}-\d{2}$/.test(f.expected_delivery_date || '')
      )
    }

    const submit = async () => {
      if (submitting.value) return
      if (!isValid()) {
        error.value = t('purchaseOrder.required')
        return
      }
      try {
        submitting.value = true
        error.value = null
        const created = await api.createPurchaseOrder({
          backlog_item_id: props.backlogItem.id,
          supplier_name: form.value.supplier_name.trim(),
          quantity: form.value.quantity,
          unit_cost: form.value.unit_cost,
          expected_delivery_date: form.value.expected_delivery_date,
          notes: form.value.notes ? form.value.notes.trim() : null
        })
        purchaseOrder.value = created
        emit('po-created', created)
      } catch (err) {
        const detail = err.response && err.response.data && err.response.data.detail
        error.value = typeof detail === 'string'
          ? `${t('purchaseOrder.submitError')}: ${detail}`
          : t('purchaseOrder.submitError')
        console.error('Failed to create purchase order:', err)
      } finally {
        submitting.value = false
      }
    }

    const close = () => {
      emit('close')
    }

    const formatDateTime = (value) => {
      if (!value) return '-'
      const date = new Date(value)
      return isNaN(date.getTime()) ? value : date.toLocaleString()
    }

    // Prepare the form or fetch the PO each time the modal opens or switches mode.
    // After a successful create, the parent switches to 'view' and the PO is already in hand.
    watch(
      () => [props.isOpen, props.mode, props.backlogItem && props.backlogItem.id],
      ([isOpen, mode], oldValue) => {
        if (!isOpen || !props.backlogItem) return
        const [wasOpen, oldMode] = oldValue || []
        error.value = null
        if (mode === 'create') {
          purchaseOrder.value = null
          resetForm()
        } else if (!(wasOpen && oldMode === 'create' && purchaseOrder.value)) {
          loadPurchaseOrder()
        }
      },
      { immediate: true }
    )

    return {
      t,
      currentCurrency,
      translateProductName,
      formatCurrencyWithDecimals,
      form,
      formTotal,
      shortage,
      submitting,
      loading,
      error,
      purchaseOrder,
      today,
      submit,
      close,
      formatDateTime
    }
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 1rem;
}

.modal-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);
  max-width: 560px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.close-button {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 0.5rem;
  display: flex;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.close-button:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

.item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding-bottom: 1.25rem;
  margin-bottom: 1.25rem;
  border-bottom: 1px solid #e2e8f0;
}

.item-name {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 0.25rem 0;
}

.item-sku,
.mono {
  font-size: 0.875rem;
  color: #64748b;
  font-family: 'Monaco', 'Courier New', monospace;
}

.shortage {
  text-align: right;
  flex-shrink: 0;
}

.shortage-label,
.field-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
}

.shortage-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #dc2626;
}

.po-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  flex: 1;
}

.field-row {
  display: flex;
  gap: 1rem;
}

.field input,
.field textarea {
  padding: 0.625rem 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 0.938rem;
  font-family: inherit;
  color: #0f172a;
}

.field input:focus,
.field textarea:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.total-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: #f8fafc;
  border-radius: 8px;
  color: #334155;
}

.error-message {
  margin: 0;
  padding: 0.75rem 1rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #b91c1c;
  font-size: 0.875rem;
}

.state-message {
  color: #64748b;
  padding: 1rem 0;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.25rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.info-item.full {
  grid-column: 1 / -1;
}

.info-value {
  font-size: 0.938rem;
  color: #0f172a;
  font-weight: 500;
}

.info-value.mono {
  color: #2563eb;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.625rem;
  border-radius: 6px;
  background: #dbeafe;
  color: #1e40af;
  font-size: 0.813rem;
  font-weight: 600;
}

.modal-footer {
  padding: 1.25rem 1.5rem;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.btn-secondary,
.btn-primary {
  padding: 0.625rem 1.25rem;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.btn-secondary {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  color: #334155;
}

.btn-secondary:hover {
  background: #e2e8f0;
}

.btn-primary {
  background: #3b82f6;
  border: 1px solid #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 480px) {
  .field-row,
  .item-header {
    flex-direction: column;
    align-items: stretch;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
